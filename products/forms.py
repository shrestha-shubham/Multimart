from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ('rating', 'comment')
        widgets = {
            'rating': forms.NumberInput(attrs={
                'min': 1,
                'max': 5,
                'step': 1,
                'class': 'w-full rounded-lg border border-stone-300 px-3 py-2 text-sm',
            }),
            'comment': forms.Textarea(attrs={
                'rows': 4,
                'class': 'w-full rounded-lg border border-stone-300 px-3 py-2 text-sm',
                'placeholder': 'Share your experience with this product',
            }),
        }