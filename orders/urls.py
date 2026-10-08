from django.urls import path
from .views import (
    add_to_cart,
    cart,
    checkout,
    order_confirmation,
    remove_cart_item,
    update_cart_item,
)

urlpatterns = [
    path('cart/', cart, name='cart'),
    path('checkout/', checkout, name='checkout'),
    path('orders/placed/<str:order_number>/', order_confirmation, name='order-confirmation'),
    path('cart/items/<int:item_id>/update/', update_cart_item, name='update-cart-item'),
    path('cart/items/<int:item_id>/remove/', remove_cart_item, name='remove-cart-item'),
    path(
        'cart/add/<int:product_id>/',
        add_to_cart,
        name='add-to-cart'
    ),
]