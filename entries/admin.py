from django.contrib import admin

from .models import Entry


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ["key", "owner", "updated_at"]
    search_fields = ["key", "owner__username"]
    readonly_fields = ["created_at", "updated_at"]
    list_select_related = ["owner"]
