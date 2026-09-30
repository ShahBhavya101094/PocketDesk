from django.contrib import admin

from .models import Task


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "completed", "owner", "updated_at"]
    list_filter = ["completed"]
    search_fields = ["title", "owner__username"]
    readonly_fields = ["created_at", "updated_at"]
    list_select_related = ["owner"]
