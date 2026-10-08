from django import forms

from products.models import Product
from .models import Store


FIELD_CLASSES = (
    'w-full rounded-xl border border-stone-300 bg-white px-4 py-3 '
    'text-sm text-slate-800 outline-none transition '
    'focus:border-emerald-700 focus:ring-4 focus:ring-emerald-900/10'
)


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ('category', 'name', 'description', 'price', 'stock', 'image', 'is_active')
        widgets = {
            'category': forms.Select(attrs={'class': FIELD_CLASSES}),
            'name': forms.TextInput(attrs={'class': FIELD_CLASSES, 'placeholder': 'Product name'}),
            'description': forms.Textarea(attrs={'class': FIELD_CLASSES, 'rows': 4, 'placeholder': 'Describe your product'}),
            'price': forms.NumberInput(attrs={'class': FIELD_CLASSES, 'min': '0.01', 'step': '0.01', 'placeholder': '0.00'}),
            'stock': forms.NumberInput(attrs={'class': FIELD_CLASSES, 'min': '0', 'step': '1', 'placeholder': '0'}),
            'image': forms.ClearableFileInput(attrs={'class': FIELD_CLASSES, 'accept': 'image/*'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'h-4 w-4 rounded border-stone-300 accent-emerald-700'}),
        }


class StoreProfileForm(forms.ModelForm):
    class Meta:
        model = Store
        fields = ('name', 'description', 'phone', 'address')
        widgets = {
            'name': forms.TextInput(attrs={'class': FIELD_CLASSES, 'placeholder': 'Store name'}),
            'description': forms.Textarea(attrs={'class': FIELD_CLASSES, 'rows': 4, 'placeholder': 'Tell customers about your store'}),
            'phone': forms.TextInput(attrs={'class': FIELD_CLASSES, 'placeholder': 'Contact phone'}),
            'address': forms.TextInput(attrs={'class': FIELD_CLASSES, 'placeholder': 'Store address'}),
        }
