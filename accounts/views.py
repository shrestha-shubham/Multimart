from datetime import timedelta
from functools import wraps

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Avg, Count, Sum
from django.db.models.functions import TruncDate
from django.shortcuts import redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone

from orders.models import Order, OrderItem
from products.models import Product, Review
from sellers.models import Store

from .forms import ProfileForm, RegistrationForm


def seller_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        if request.user.is_staff or request.user.is_superuser:
            raise PermissionDenied

        if request.user.role != 'seller':
            raise PermissionDenied

        return view_func(request, *args, **kwargs)

    return wrapper


def customer_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')

        if request.user.is_staff or request.user.is_superuser:
            raise PermissionDenied

        if request.user.role != 'customer':
            raise PermissionDenied

        return view_func(request, *args, **kwargs)

    return wrapper


def admin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.is_staff or request.user.is_superuser):
            raise PermissionDenied
        return view_func(request, *args, **kwargs)

    return wrapper


def login_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    context = {
        'google_login_enabled': bool(
            settings.GOOGLE_OAUTH_CLIENT_ID and settings.GOOGLE_OAUTH_CLIENT_SECRET
        ),
    }

    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None:
            login(request, user)
            return redirect('dashboard')

        return render(
            request,
            'accounts/login.html',
            {**context, 'error': 'Invalid username or password.'}
        )

    return render(request, 'accounts/login.html', context)


def register_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')

    form = RegistrationForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            user = form.save()
            if user.role == 'seller':
                Store.objects.create(
                    owner=user,
                    name=form.cleaned_data['store_name'],
                    phone=form.cleaned_data['phone'],
                    address=form.cleaned_data['address'],
                )
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        return redirect('dashboard')

    return render(request, 'accounts/register.html', {'form': form})


@login_required
def dashboard(request):
    if request.user.is_staff or request.user.is_superuser:
        return redirect('admin-dashboard')

    if request.user.role == 'seller':
        store = Store.objects.filter(owner=request.user).first()
        if store is None:
            seller_context = {'store': None, 'recent_reviews': []}
        else:
            store_reviews = Review.objects.filter(product__store=store)
            delivered_items = OrderItem.objects.filter(
                store=store,
                order__delivery_status='delivered',
            )
            seller_context = {
                'store': store,
                'total_products': store.products.count(),
                'total_earnings': delivered_items.aggregate(total=Sum('subtotal'))['total'] or 0,
                'total_orders': store.order_items.values('order_id').distinct().count(),
                'total_ratings': store_reviews.count(),
                'average_rating': store_reviews.aggregate(average=Avg('rating'))['average'],
                'total_reviews': store_reviews.count(),
                'recent_reviews': store_reviews.select_related(
                    'customer', 'product', 'product__category'
                ).order_by('-created_at')[:6],
            }
        return render(request, 'accounts/seller_dashboard.html', seller_context)

    if request.user.role == 'customer':
        return render(request, 'accounts/customer_dashboard.html')

    raise PermissionDenied


@admin_required
def admin_dashboard(request):
    today = timezone.localdate()
    start_date = today - timedelta(days=6)
    daily_counts = {
        row['day']: row['order_count']
        for row in Order.objects.filter(
            created_at__date__gte=start_date,
            created_at__date__lte=today,
        ).annotate(day=TruncDate('created_at'))
        .values('day')
        .annotate(order_count=Count('id'))
    }
    max_daily_count = max(daily_counts.values(), default=0)
    orders_by_day = []
    for offset in range(7):
        day = start_date + timedelta(days=offset)
        count = daily_counts.get(day, 0)
        orders_by_day.append({
            'day': day,
            'label': day.strftime('%b %d'),
            'count': count,
            'height': max(6, round(count * 100 / max_daily_count)) if max_daily_count else 6,
        })

    return render(request, 'accounts/admin_dashboard.html', {
        'active_page': 'dashboard',
        'total_products': Product.objects.count(),
        'total_revenue': Order.objects.aggregate(total=Sum('total_amount'))['total'] or 0,
        'total_orders': Order.objects.count(),
        'total_stores': Store.objects.count(),
        'orders_by_day': orders_by_day,
        'recent_orders': Order.objects.select_related('customer').order_by('-created_at')[:8],
        'recent_stores': Store.objects.select_related('owner').order_by('-created_at')[:5],
    })


@admin_required
def admin_stores(request):
    return render(request, 'accounts/admin_stores.html', {
        'active_page': 'stores',
        'stores': Store.objects.select_related('owner').annotate(
            product_count=Count('products'),
        ).order_by('name'),
    })


@login_required
def profile(request):
    if request.user.is_staff or request.user.is_superuser:
        return redirect('dashboard')
    if request.user.role == 'seller':
        return redirect('seller_profile')
    if request.user.role != 'customer':
        return redirect('dashboard')

    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated.')
            return redirect('profile')
    else:
        form = ProfileForm(instance=request.user)

    return render(request, 'accounts/profile.html', {'form': form})


@seller_required
def seller_area(request):
    return render(request, 'accounts/seller_dashboard.html')


@customer_required
def customer_area(request):
    return render(request, 'accounts/customer_dashboard.html')


@login_required
def logout_view(request):
    next_url = request.GET.get('next')
    logout(request)
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect(next_url)
    return redirect('login')
