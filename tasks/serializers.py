from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Task
from .validators import normalize_title


class TaskSerializer(serializers.ModelSerializer):
    owner = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = Task
        fields = ["id", "title", "completed", "owner", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_title(self, value):
        try:
            return normalize_title(value)
        except DjangoValidationError as exc:
            raise serializers.ValidationError(exc.messages) from exc
