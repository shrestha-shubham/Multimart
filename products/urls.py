from django.urls import path
from .views import ProductListAPIView, product_detail, submit_review

urlpatterns = [
    path('products/', ProductListAPIView.as_view(), name='product-list'),
    path(
        'product/<int:product_id>/',
        product_detail,
        name='product-detail'
    ),
    path('product/<int:product_id>/review/', submit_review, name='submit-review'),
]