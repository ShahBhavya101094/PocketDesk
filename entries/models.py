from django.conf import settings
from django.db import models

from .validators import validate_key, validate_value


class Entry(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="entries"
    )
    key = models.CharField(max_length=80, validators=[validate_key])
    value = models.TextField(max_length=5000, validators=[validate_value])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key", "id"]
        constraints = [
            models.UniqueConstraint(fields=["owner", "key"], name="unique_entry_owner_key")
        ]

    def clean(self):
        # Forms call this through full_clean(). Scripts must call full_clean()
        # explicitly before save(); only uniqueness is also a DB constraint.
        super().clean()
        # The field validators report errors; only canonicalize here so forms
        # do not receive duplicate non-field errors for an invalid field.
        if isinstance(self.key, str):
            self.key = self.key.strip().lower()
        if isinstance(self.value, str):
            self.value = self.value.strip()

    def __str__(self):
        return self.key
