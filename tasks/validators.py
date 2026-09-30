"""One title rule shared by HTML forms, the API, and model validation."""

from django.core.exceptions import ValidationError


def normalize_title(value):
    title = value.strip()
    if len(title) < 3:
        raise ValidationError("Use at least 3 characters.", code="min_length")
    if len(title) > 200:
        raise ValidationError("Use at most 200 characters.", code="max_length")
    return title


def validate_title(value):
    # Validators check a value; normalization happens in clean/serializer methods.
    normalize_title(value)
