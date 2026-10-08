from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from products.views import home
from sellers.views import public_store_profile


urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('', home, name='home'),
    path('stores/<int:store_id>/', public_store_profile, name='store-profile'),
    path('', include('accounts.urls')),
    path('', include('orders.urls')),
    path('api/', include('products.urls')),
    path('seller/', include('sellers.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
