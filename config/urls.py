from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from django.views.decorators.http import require_safe
from django.views.generic import RedirectView
from rest_framework.routers import DefaultRouter

from entries.api import EntryViewSet
from tasks.api import TaskViewSet

router = DefaultRouter()
router.register("tasks", TaskViewSet, basename="task")
router.register("entries", EntryViewSet, basename="entry")


@require_safe
def healthz(request):
    """Liveness only: deliberately does not test database readiness."""
    response = JsonResponse({"status": "ok"})
    response["Cache-Control"] = "no-store"
    return response


urlpatterns = [
    path("", RedirectView.as_view(pattern_name="tasks:list", permanent=False)),
    path("healthz/", healthz, name="healthz"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("tasks/", include("tasks.urls")),
    path("entries/", include("entries.urls")),
    path("api/", include(router.urls)),
    path("api-auth/", include("rest_framework.urls", namespace="rest_framework")),
]
