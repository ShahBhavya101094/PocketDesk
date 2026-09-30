from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Entry
from .validators import DUPLICATE_KEY_MESSAGE, normalize_key, normalize_value


class EntrySerializer(serializers.ModelSerializer):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Entry
        fields = ["id", "key", "value", "owner", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
        # Validate normalized keys explicitly; also handle owner on partial updates.
        validators = []

    def validate_key(self, value):
        try:
            return normalize_key(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc

    def validate_value(self, value):
        try:
            return normalize_value(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc

    def validate(self, attrs):
        owner = self.context["request"].user
        key = attrs.get("key", self.instance.key if self.instance else None)
        duplicates = Entry.objects.filter(owner=owner, key=key)
        if self.instance:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise serializers.ValidationError({"key": DUPLICATE_KEY_MESSAGE})
        return attrs
