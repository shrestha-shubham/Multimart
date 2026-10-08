import re

from django.core.exceptions import ValidationError


def validate_nepal_mobile(value):
    """Accept 10-digit Nepali mobile numbers, optionally prefixed with +977."""
    digits = re.sub(r'[\s()-]', '', value or '')
    if not re.fullmatch(r'(?:\+?977)?9[678]\d{8}', digits):
        raise ValidationError(
            'Enter a valid Nepal mobile number, such as 98XXXXXXXX or +977 98XXXXXXXX.'
        )
    return value
