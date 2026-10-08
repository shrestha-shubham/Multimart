from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from rest_framework.generics import ListAPIView

from orders.models import OrderItem

from .forms import ReviewForm
from .models import Category, Product, Review
from .serializers import ProductSerializer


def home(request):
    products = Product.objects.filter(is_active=True).select_related('store')
    search_query = request.GET.get('q', '').strip()
    if search_query:
        products = products.filter(name__icontains=search_query)

    categories = Category.objects.filter(products__is_active=True)
    if search_query:
        categories = categories.filter(products__name__icontains=search_query)
    categories = categories.distinct().order_by('name').prefetch_related(
        Prefetch(
            'products',
            queryset=products.order_by('-created_at'),
        )
    )
    return render(
        request,
        'products/home.html',
        {
            'categories': categories,
            'uncategorized_products': products.filter(category__isnull=True),
            'search_query': search_query,
        }
    )
def product_detail(request, product_id):
    product = get_object_or_404(
        Product.objects.select_related('store', 'category'),
        id=product_id,
        is_active=True,
    )
    reviews = product.reviews.select_related('customer').all()
    can_review = request.user.is_authenticated and OrderItem.objects.filter(
        product=product,
        order__customer=request.user,
        order__delivery_status='delivered',
    ).exists()
    existing_review = reviews.filter(customer=request.user).first() if can_review else None

    return render(
        request,
        'products/product_detail.html',
        {
            'product': product,
            'reviews': reviews,
            'review_count': reviews.count(),
            'average_rating': reviews.aggregate(average=Avg('rating'))['average'],
            'can_review': can_review,
            'existing_review': existing_review,
            'review_form': ReviewForm(instance=existing_review),
        }
    )


@login_required
@require_POST
def submit_review(request, product_id):
    product = get_object_or_404(Product, pk=product_id, is_active=True)
    order_item = OrderItem.objects.filter(
        product=product,
        order__customer=request.user,
        order__delivery_status='delivered',
    ).order_by('-order__created_at').first()
    if order_item is None:
        messages.error(request, 'A delivered purchase is required to review this product.')
        return redirect('product-detail', product_id=product.pk)

    review = Review.objects.filter(product=product, customer=request.user).first()
    form = ReviewForm(request.POST, instance=review)
    if form.is_valid():
        review = form.save(commit=False)
        review.product = product
        review.customer = request.user
        review.order_item = order_item
        review.save()
        messages.success(request, 'Your product review has been saved.')
    else:
        messages.error(request, 'Enter a rating from 1 to 5 and a review comment.')
    return redirect('product-detail', product_id=product.pk)


class ProductListAPIView(ListAPIView):
    serializer_class = ProductSerializer

    def get_queryset(self):
        return Product.objects.filter(is_active=True)