from uuid import uuid4
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from products.models import Product

from .forms import DeliveryAddressForm
from .location_data import LOCATION_HIERARCHY
from .models import Cart, CartItem, Coupon, CustomerAddress, Order, OrderItem


def _cart_items_and_total(cart):
    cart_items = list(
        cart.items.select_related('product', 'product__store')
        .order_by('product__store__name', 'product__name')
    )
    total = 0

    for item in cart_items:
        item.subtotal = item.product.price * item.quantity
        total += item.subtotal

    return cart_items, total


@login_required
def cart(request):
    cart, created = Cart.objects.get_or_create(
        customer=request.user
    )
    cart_items, total = _cart_items_and_total(cart)

    return render(
        request,
        'orders/cart.html',
        {
            'cart': cart,
            'cart_items': cart_items,
            'total': total,
        }
    )

@login_required
def checkout(request):
    cart = Cart.objects.filter(customer=request.user).first()
    if cart is None:
        messages.info(request, 'Add products to your cart before checking out.')
        return redirect('cart')

    cart_items, total = _cart_items_and_total(cart)
    if not cart_items:
        messages.info(request, 'Add products to your cart before checking out.')
        return redirect('cart')

    saved_address = CustomerAddress.objects.filter(customer=request.user).first()
    address_initial = {
        'full_name': saved_address.full_name if saved_address else request.user.get_full_name() or request.user.username,
        'phone': saved_address.phone if saved_address else '',
        'province': saved_address.province if saved_address else '',
        'district': saved_address.district if saved_address else '',
        'municipality': saved_address.municipality if saved_address else '',
        'ward': saved_address.ward if saved_address else '',
        'tole': saved_address.tole if saved_address else '',
        'landmark': saved_address.landmark if saved_address else '',
        'save_address': bool(saved_address),
    }
    delivery_form = DeliveryAddressForm(request.POST if request.method == 'POST' else None, initial=address_initial)
    form_values = {
        'payment_method': 'cod',
        'coupon_code': '',
    }
    errors = []
    discount_amount = Decimal('0.00')
    coupon = None

    if request.method == 'POST':
        form_values = {
            'payment_method': request.POST.get('payment_method', ''),
            'coupon_code': request.POST.get('coupon_code', '').strip().upper(),
        }
        address_valid = delivery_form.is_valid()
        if form_values['payment_method'] != 'cod':
            errors.append('Online payment is not available yet. Choose Cash on Delivery.')
        if form_values['coupon_code']:
            coupon = Coupon.objects.filter(code__iexact=form_values['coupon_code']).first()
            if coupon is None or not coupon.is_valid_now:
                errors.append('That coupon is invalid, expired, or has reached its usage limit.')

        if not errors and address_valid:
            address_data = delivery_form.cleaned_data
            order_error = None
            order = None

            with transaction.atomic():
                locked_items = list(
                    CartItem.objects.select_for_update()
                    .filter(cart=cart)
                    .order_by('product_id')
                )
                product_ids = [item.product_id for item in locked_items]
                locked_products = {
                    product.pk: product
                    for product in Product.objects.select_for_update()
                    .filter(pk__in=product_ids)
                    .order_by('pk')
                }

                if not locked_items:
                    order_error = 'Your cart is empty.'
                else:
                    for item in locked_items:
                        product = locked_products.get(item.product_id)
                        if product is None or not product.is_active:
                            order_error = 'A product in your cart is no longer available.'
                            break
                        if product.store.owner_id == request.user.pk:
                            order_error = f'You cannot purchase your own product: {product.name}.'
                            break
                        if item.quantity > product.stock:
                            order_error = f'Only {product.stock} of {product.name} are available. Update your cart and try again.'
                            break

                locked_coupon = None
                if order_error is None and coupon is not None:
                    locked_coupon = Coupon.objects.select_for_update().get(pk=coupon.pk)
                    if not locked_coupon.is_valid_now:
                        order_error = 'That coupon is no longer available. Review it and try again.'

                if order_error is None:
                    subtotal = sum(
                        (locked_products[item.product_id].price * item.quantity for item in locked_items),
                        Decimal('0.00'),
                    )
                    discount_amount = Decimal('0.00')
                    if locked_coupon is not None:
                        if locked_coupon.discount_type == 'percent':
                            discount_amount = (subtotal * locked_coupon.discount_value / 100).quantize(Decimal('0.01'))
                        else:
                            discount_amount = min(subtotal, locked_coupon.discount_value)
                    order_total = subtotal - discount_amount
                    order = Order.objects.create(
                        customer=request.user,
                        order_number=f'MM{uuid4().hex[:12].upper()}',
                        total_amount=order_total,
                        discount_amount=discount_amount,
                        coupon=locked_coupon,
                        payment_method='cod',
                        delivery_name=address_data['full_name'],
                        delivery_phone=address_data['phone'],
                        delivery_address=delivery_form.address_snapshot(),
                        delivery_province=address_data['province'],
                        delivery_district=address_data['district'],
                        delivery_municipality=address_data['municipality'],
                        delivery_ward=address_data['ward'],
                        delivery_tole=address_data['tole'],
                        delivery_landmark=address_data['landmark'],
                    )

                    if address_data['save_address']:
                        CustomerAddress.objects.update_or_create(
                            customer=request.user,
                            defaults={
                                'full_name': address_data['full_name'],
                                'phone': address_data['phone'],
                                'province': address_data['province'],
                                'district': address_data['district'],
                                'municipality': address_data['municipality'],
                                'ward': address_data['ward'],
                                'tole': address_data['tole'],
                                'landmark': address_data['landmark'],
                            },
                        )

                    for item in locked_items:
                        product = locked_products[item.product_id]
                        subtotal = product.price * item.quantity
                        OrderItem.objects.create(
                            order=order,
                            product=product,
                            store=product.store,
                            quantity=item.quantity,
                            unit_price=product.price,
                            subtotal=subtotal,
                        )
                        product.stock -= item.quantity
                        product.save(update_fields=['stock', 'updated_at'])

                    cart.items.filter(pk__in=[item.pk for item in locked_items]).delete()
                    if locked_coupon is not None:
                        locked_coupon.usage_count += 1
                        locked_coupon.save(update_fields=['usage_count'])

            if order_error:
                messages.error(request, order_error)
                return redirect('cart')

            return redirect('order-confirmation', order_number=order.order_number)

    return render(request, 'orders/checkout.html', {
        'cart_items': cart_items,
        'total': total,
        'subtotal': total,
        'discount_amount': discount_amount,
        'final_total': total - discount_amount,
        'coupon': coupon,
        'form_values': form_values,
        'delivery_form': delivery_form,
        'location_hierarchy': LOCATION_HIERARCHY,
        'errors': errors,
    })


@login_required
@require_POST
def add_to_cart(request, product_id):
    product = get_object_or_404(
        Product,
        id=product_id,
        is_active=True
    )

    if product.store.owner_id == request.user.pk:
        messages.error(request, 'You cannot add your own product to the cart.')
        return redirect('product-detail', product_id=product.pk)

    try:
        quantity = int(request.POST.get('quantity', '1'))
    except (TypeError, ValueError):
        messages.error(request, 'Enter a valid product quantity.')
        return redirect('product-detail', product_id=product.pk)

    if quantity < 1:
        messages.error(request, 'Product quantity must be at least one.')
        return redirect('product-detail', product_id=product.pk)

    cart, created = Cart.objects.get_or_create(
        customer=request.user
    )

    with transaction.atomic():
        cart_item, created = CartItem.objects.select_for_update().get_or_create(
            cart=cart,
            product=product
        )
        new_quantity = quantity if created else cart_item.quantity + quantity

        if quantity > product.stock or new_quantity > product.stock:
            if created:
                cart_item.delete()
            messages.error(request, f'Only {product.stock} of {product.name} are available.')
            return redirect('product-detail', product_id=product.pk)

        cart_item.quantity = new_quantity
        cart_item.save(update_fields=['quantity'])

    return redirect('cart')


@login_required
@require_POST
def update_cart_item(request, item_id):
    cart_item = get_object_or_404(
        CartItem,
        pk=item_id,
        cart__customer=request.user,
    )

    try:
        quantity = int(request.POST.get('quantity', ''))
    except (TypeError, ValueError):
        messages.error(request, 'Enter a valid product quantity.')
        return redirect('cart')

    if not 1 <= quantity <= cart_item.product.stock:
        messages.error(request, f'Choose a quantity between 1 and {cart_item.product.stock}.')
        return redirect('cart')

    cart_item.quantity = quantity
    cart_item.save(update_fields=['quantity'])
    return redirect('cart')


@login_required
@require_POST
def remove_cart_item(request, item_id):
    cart_item = get_object_or_404(
        CartItem,
        pk=item_id,
        cart__customer=request.user,
    )
    cart_item.delete()
    return redirect('cart')


@login_required
def order_confirmation(request, order_number):
    order = get_object_or_404(
        Order.objects.prefetch_related('items__product', 'items__store'),
        order_number=order_number,
        customer=request.user,
    )
    return render(request, 'orders/order_confirmation.html', {'order': order})
