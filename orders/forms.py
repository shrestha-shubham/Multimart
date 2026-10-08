from django import forms

from accounts.validators import validate_nepal_mobile

from .location_data import LOCATION_HIERARCHY, MAX_WARD_NUMBER, PROVINCES


INPUT_CLASS = (
    'w-full rounded-xl border border-stone-300 bg-white px-4 py-3 text-sm '
    'outline-none transition focus:border-[#087466] focus:ring-4 '
    'focus:ring-emerald-900/10'
)


class DeliveryAddressForm(forms.Form):
    full_name = forms.CharField(max_length=150, label='Full Name')
    phone = forms.CharField(max_length=30, label='Phone Number', validators=[validate_nepal_mobile])
    province = forms.ChoiceField(choices=[('', 'Select province'), *((item, item) for item in PROVINCES)])
    district = forms.ChoiceField(choices=[('', 'Select district')])
    municipality = forms.ChoiceField(
        label='Municipality / Rural Municipality',
        choices=[('', 'Select municipality or rural municipality')],
    )
    ward = forms.IntegerField(
        min_value=1,
        max_value=MAX_WARD_NUMBER,
        label='Ward Number',
        widget=forms.NumberInput(attrs={'min': 1, 'max': MAX_WARD_NUMBER, 'inputmode': 'numeric'}),
    )
    tole = forms.CharField(max_length=150, label='Tole / Street')
    landmark = forms.CharField(max_length=255, required=False, label='House No. / Landmark')
    save_address = forms.BooleanField(required=False, label='Save this address for next time')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        values = self.data if self.is_bound else self.initial
        province = values.get('province', '')
        district = values.get('district', '')
        province_districts = LOCATION_HIERARCHY.get(province, {})
        self.fields['district'].choices = [
            ('', 'Select district'),
            *((name, name) for name in province_districts),
        ]
        self.fields['municipality'].choices = [
            ('', 'Select municipality or rural municipality'),
            *((name, name) for name in province_districts.get(district, ())),
        ]

        for name, field in self.fields.items():
            field.widget.attrs.setdefault('class', INPUT_CLASS)
            field.widget.attrs.setdefault('id', f'id_{name}')
        self.fields['full_name'].widget.attrs.update({'autocomplete': 'name'})
        self.fields['phone'].widget.attrs.update({
            'autocomplete': 'tel',
            'placeholder': '98XXXXXXXX or +977 98XXXXXXXX',
            'type': 'tel',
        })
        self.fields['tole'].widget.attrs.update({'autocomplete': 'street-address'})
        self.fields['landmark'].widget.attrs.update({'placeholder': 'Optional'})
        self.fields['save_address'].widget.attrs.update({'class': 'h-4 w-4 accent-[#087466]'})

    def clean(self):
        cleaned_data = super().clean()
        province = cleaned_data.get('province')
        district = cleaned_data.get('district')
        municipality = cleaned_data.get('municipality')

        if province and district and district not in LOCATION_HIERARCHY.get(province, {}):
            self.add_error('district', 'Choose a district in the selected province.')
        elif province and district and municipality and municipality not in LOCATION_HIERARCHY[province][district]:
            self.add_error('municipality', 'Choose a municipality in the selected district.')
        return cleaned_data

    def address_snapshot(self):
        data = self.cleaned_data
        parts = [
            f"Ward {data['ward']}, {data['tole']}",
            data['municipality'],
            data['district'],
            data['province'],
            'Nepal',
        ]
        if data.get('landmark'):
            parts.insert(0, data['landmark'])
        return ', '.join(parts)
