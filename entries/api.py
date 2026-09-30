import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from .models import Entry
from .serializers import EntrySerializer
from .validators import DUPLICATE_KEY_MESSAGE, normalize_key

logger = logging.getLogger(__name__)


class EntryViewSet(ModelViewSet):
    serializer_class = EntrySerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["key", "value"]
    ordering_fields = ["id", "key", "created_at", "updated_at"]
    ordering = ["key", "id"]

    def get_queryset(self):
        return Entry.objects.filter(owner=self.request.user)

    def _save_with_owner(self, serializer):
        existing = serializer.instance
        key = serializer.validated_data.get("key", existing.key if existing else None)
        try:
            with transaction.atomic():
                serializer.save(owner=self.request.user)
        except IntegrityError as exc:
            # The DB constraint is the final defense against two simultaneous creates.
            duplicates = self.get_queryset().filter(key=key)
            if existing:
                duplicates = duplicates.exclude(pk=existing.pk)
            if not duplicates.exists():
                raise
            logger.info("Concurrent duplicate entry rejected in REST API")
            raise serializers.ValidationError({"key": DUPLICATE_KEY_MESSAGE}) from exc

    def perform_create(self, serializer):
        self._save_with_owner(serializer)

    def perform_update(self, serializer):
        self._save_with_owner(serializer)

    @action(detail=False, methods=["get"], url_path="by-key")
    def by_key(self, request):
        """GET /api/entries/by-key/?key=course_link returns one owned note."""
        try:
            key = normalize_key(request.query_params.get("key", ""))
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"key": exc.messages}) from exc
        entry = get_object_or_404(self.get_queryset(), key=key)
        return Response(self.get_serializer(entry).data)
