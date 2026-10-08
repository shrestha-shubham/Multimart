from django.contrib import messages
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.db.models import Prefetch

from accounts.views import seller_required
from products.models import Product

from .forms import ProductForm, StoreProfileForm
from .models import Store


@seller_required
def product_list(request):
    store = Store.objects.filter(owner=request.user).first()
    query = request.GET.get('q', '').strip()
    products = Product.objects.none()

    if store is not None:
        products = store.products.select_related('category').order_by('-created_at')
        if query:
            products = products.filter(
                Q(name__icontains=query) | Q(category__name__icontains=query)
            )

    return render(request, 'sellers/products.html', {
        'store': store,
        'products': products,
        'query': query,
    })


@seller_required
def product_add(request):
    store = Store.objects.filter(owner=request.user).first()
    if store is None:
        messages.info(request, 'Create your store profile before adding products.')
        return redirect('seller_profile')

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.store = store
            product.save()
            messages.success(request, 'Product added to your store.')
            return redirect('seller_products')
    else:
        form = ProductForm()

    return render(request, 'sellers/product_form.html', {
        'form': form,
        'store': store,
        'page_title': 'Add Product',
        'submit_label': 'Add Product',
    })


@seller_required
def product_edit(request, product_id):
    product = get_object_or_404(
        Product,
        pk=product_id,
        store__owner=request.user,
    )

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, 'Product updated.')
            return redirect('seller_products')
    else:
        form = ProductForm(instance=product)

    return render(request, 'sellers/product_form.html', {
        'form': form,
        'store': product.store,
        'product': product,
        'page_title': 'Edit Product',
        'submit_label': 'Save Changes',
    })


@seller_required
@require_POST
def product_delete(request, product_id):
    product = get_object_or_404(Product, pk=product_id, store__owner=request.user)
    try:
        product.delete()
    except ProtectedError:
        messages.error(request, 'This product is part of an order and cannot be deleted.')
    else:
        messages.success(request, 'Product deleted from your store.')
    return redirect('seller_products')


@seller_required
def profile_edit(request):
    store = Store.objects.filter(owner=request.user).first()

    if request.method == 'POST':
        form = StoreProfileForm(request.POST, instance=store)
        if form.is_valid():
            store = form.save(commit=False)
            store.owner = request.user
            store.save()
            messages.success(request, 'Store profile saved.')
            return redirect('seller_profile')
    else:
        form = StoreProfileForm(instance=store)

    return render(request, 'sellers/profile_form.html', {
        'form': form,
        'store': store,
    })


def public_store_profile(request, store_id):
    store = get_object_or_404(
        Store.objects.prefetch_related(
            Prefetch(
                'products',
                queryset=Product.objects.filter(is_active=True)
                .select_related('category')
                .order_by('-created_at'),
            )
        ),
        pk=store_id,
    )
    return render(request, 'sellers/public_store.html', {'store': store})
