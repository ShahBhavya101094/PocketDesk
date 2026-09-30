import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .forms import EntryForm
from .models import Entry
from .validators import DUPLICATE_KEY_MESSAGE

logger = logging.getLogger(__name__)


@login_required
def entry_list(request):
    owned = Entry.objects.filter(owner=request.user)
    query = request.GET.get("q", "").strip()[:200]
    entries = owned
    if query:
        entries = entries.filter(Q(key__icontains=query) | Q(value__icontains=query))
    page_obj = Paginator(entries.order_by("key", "id"), 10).get_page(request.GET.get("page"))
    return render(
        request,
        "entries/list.html",
        {
            "page_obj": page_obj,
            "entries": page_obj,
            "query": query,
            "status": "all",
            "total_count": owned.count(),
        },
    )


def _save_form(form, user):
    """Keep a concurrent duplicate as a form error, not an HTTP 500."""
    entry = form.save(commit=False)
    entry.owner = user
    try:
        # Catch outside the savepoint, so the connection remains usable afterwards.
        with transaction.atomic():
            entry.save()
    except IntegrityError:
        duplicates = Entry.objects.filter(owner=user, key=entry.key)
        if entry.pk:
            duplicates = duplicates.exclude(pk=entry.pk)
        if not duplicates.exists():
            raise
        logger.info("Concurrent duplicate entry rejected in HTML form")
        form.add_error("key", DUPLICATE_KEY_MESSAGE)
        return False
    return True


@login_required
def entry_create(request):
    form = EntryForm(request.POST if request.method == "POST" else None, user=request.user)
    if request.method == "POST" and form.is_valid() and _save_form(form, request.user):
        messages.success(request, "Note saved.")
        return redirect("entries:list")
    return render(request, "entries/form.html", {"form": form, "object": None, "entry": None})


@login_required
def entry_update(request, pk):
    entry = get_object_or_404(Entry.objects.filter(owner=request.user), pk=pk)
    form = EntryForm(
        request.POST if request.method == "POST" else None, instance=entry, user=request.user
    )
    if request.method == "POST" and form.is_valid() and _save_form(form, request.user):
        messages.success(request, "Note updated.")
        return redirect("entries:list")
    return render(request, "entries/form.html", {"form": form, "object": entry, "entry": entry})


@login_required
def entry_delete(request, pk):
    entry = get_object_or_404(Entry.objects.filter(owner=request.user), pk=pk)
    if request.method == "POST":
        entry.delete()
        messages.success(request, "Note deleted.")
        return redirect("entries:list")
    return render(request, "entries/confirm_delete.html", {"object": entry, "entry": entry})
