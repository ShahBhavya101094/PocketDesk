"""Normalize once and apply the same rules in forms and REST serializers."""

import re

from django.core.exceptions import ValidationError

KEY_PATTERN = re.compile(r"[a-z0-9_-]+", flags=re.ASCII)
DUPLICATE_KEY_MESSAGE = "You already have a note with this key."


def normalize_key(value):
    key = value.strip().lower()
    if not key or len(key) > 80 or KEY_PATTERN.fullmatch(key) is None:
        raise ValidationError(
            "Use 1–80 lowercase letters, digits, underscores, or hyphens.", code="invalid"
        )
    return key


def validate_key(value):
    normalize_key(value)


def normalize_value(value):
    value = value.strip()
    if not value:
        raise ValidationError("Enter a value.", code="required")
    if len(value) > 5000:
        raise ValidationError("Use at most 5000 characters.", code="max_length")
    return value


def validate_value(value):
    normalize_value(value)
