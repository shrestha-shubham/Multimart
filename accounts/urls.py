from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('admin-dashboard/', views.admin_dashboard, name='admin-dashboard'),
    path('admin-stores/', views.admin_stores, name='admin-stores'),
    path('profile/', views.profile, name='profile'),
    path('seller-area/', views.seller_area, name='seller_area'),
    path('customer-area/', views.customer_area, name='customer_area'),
    path('logout/', views.logout_view, name='logout'),
]