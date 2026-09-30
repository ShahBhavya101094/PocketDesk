from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import ModelViewSet

from .models import Task
from .serializers import TaskSerializer


class TaskViewSet(ModelViewSet):
    """HTML and API use the same model, but return different representations."""

    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated]
    search_fields = ["title"]
    ordering_fields = ["id", "title", "completed", "created_at", "updated_at"]
    ordering = ["completed", "id"]

    def get_queryset(self):
        return Task.objects.filter(owner=self.request.user)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)

    def perform_update(self, serializer):
        # PATCH omits HiddenField defaults, so keep ownership explicit here as well.
        serializer.save(owner=self.request.user)
