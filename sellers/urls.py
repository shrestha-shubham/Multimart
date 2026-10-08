from django.urls import path

from . import views

urlpatterns = [
    path('products/', views.product_list, name='seller_products'),
    path('products/add/', views.product_add, name='seller_product_add'),
    path('products/<int:product_id>/edit/', views.product_edit, name='seller_product_edit'),
    path('products/<int:product_id>/delete/', views.product_delete, name='seller_product_delete'),
    path('profile/', views.profile_edit, name='seller_profile'),
]
