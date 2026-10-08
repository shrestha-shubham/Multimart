from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    ROLE_CHOICES = (
        ('customer', 'Customer'),
        ('seller', 'Seller'),
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default='customer'
    )

    @property
    def account_category(self):
        """Return the effective UI category without granting permissions."""
        if self.is_staff or self.is_superuser:
            return 'admin'
        return self.role

    @property
    def account_category_display(self):
        if self.account_category == 'admin':
            return 'Admin'
        return self.get_role_display()
