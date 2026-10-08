from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


FIELD_CLASSES = (
    'w-full rounded-xl border border-stone-300 bg-white px-4 py-3 '
    'text-sm text-slate-800 outline-none transition '
    'focus:border-emerald-700 focus:ring-4 focus:ring-emerald-900/10'
)


class RegistrationForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': FIELD_CLASSES,
            'autocomplete': 'email',
            'placeholder': 'you@example.com',
        }),
    )
    store_name = forms.CharField(required=False, max_length=150)
    phone = forms.CharField(required=False, max_length=20)
    address = forms.CharField(required=False, max_length=255)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'role')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': FIELD_CLASSES,
                'autocomplete': 'username',
                'placeholder': 'Choose a username',
            }),
            'role': forms.Select(attrs={
                'class': FIELD_CLASSES,
                'id': 'id_role',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': FIELD_CLASSES,
            'autocomplete': 'new-password',
            'placeholder': 'Create a password',
        })
        self.fields['password2'].widget.attrs.update({
            'class': FIELD_CLASSES,
            'autocomplete': 'new-password',
            'placeholder': 'Confirm your password',
        })
        for field_name, placeholder in (
            ('store_name', 'Your store name'),
            ('phone', 'Store contact phone'),
            ('address', 'Store address'),
        ):
            self.fields[field_name].widget.attrs.update({
                'class': FIELD_CLASSES,
                'placeholder': placeholder,
            })

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('role') == 'seller':
            for field_name in ('store_name', 'phone', 'address'):
                if not cleaned_data.get(field_name):
                    self.add_error(field_name, 'This field is required for seller accounts.')
        return cleaned_data


class ProfileForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': FIELD_CLASSES,
                'autocomplete': 'given-name',
            }),
            'last_name': forms.TextInput(attrs={
                'class': FIELD_CLASSES,
                'autocomplete': 'family-name',
            }),
            'email': forms.EmailInput(attrs={
                'class': FIELD_CLASSES,
                'autocomplete': 'email',
            }),
        }
