from django.conf import settings
from django.db import models


class Store(models.Model):
    owner = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='store'
    )

    name = models.CharField(max_length=150)

    description = models.TextField(blank=True)

    phone = models.CharField(max_length=20)

    address = models.CharField(max_length=255)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name