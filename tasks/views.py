"""Small function-based views: authenticate, scope, validate, then render/save."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import TaskForm
from .models import Task


@login_required
def task_list(request):
    owned = Task.objects.filter(owner=request.user)
    counts = owned.aggregate(
        total_count=Count("id"),
        open_count=Count("id", filter=Q(completed=False)),
        completed_count=Count("id", filter=Q(completed=True)),
    )
    query = request.GET.get("q", "").strip()[:200]
    status = request.GET.get("status", "all")
    if status not in {"all", "open", "done"}:
        status = "all"
    tasks = owned
    if query:
        tasks = tasks.filter(title__icontains=query)
    if status != "all":
        tasks = tasks.filter(completed=status == "done")
    page_obj = Paginator(tasks.order_by("completed", "id"), 10).get_page(request.GET.get("page"))
    return render(
        request,
        "tasks/list.html",
        {
            "page_obj": page_obj,
            "tasks": page_obj,
            "query": query,
            "status": status,
            **counts,
        },
    )


@login_required
def task_create(request):
    form = TaskForm(request.POST if request.method == "POST" else None)
    if request.method == "POST" and form.is_valid():
        task = form.save(commit=False)
        task.owner = request.user
        task.save()
        messages.success(request, "Task created.")
        return redirect("tasks:list")
    return render(request, "tasks/form.html", {"form": form, "object": None, "task": None})


@login_required
def task_update(request, pk):
    # Scope before lookup: somebody else's identifier produces a 404, not a data leak.
    task = get_object_or_404(Task.objects.filter(owner=request.user), pk=pk)
    form = TaskForm(request.POST if request.method == "POST" else None, instance=task)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Task updated.")
        return redirect("tasks:list")
    return render(request, "tasks/form.html", {"form": form, "object": task, "task": task})


@login_required
def task_delete(request, pk):
    task = get_object_or_404(Task.objects.filter(owner=request.user), pk=pk)
    if request.method == "POST":
        task.delete()
        messages.success(request, "Task deleted.")
        return redirect("tasks:list")
    return render(request, "tasks/confirm_delete.html", {"object": task, "task": task})


@login_required
@require_POST
def task_toggle(request, pk):
    task = get_object_or_404(Task.objects.filter(owner=request.user), pk=pk)
    # An SQL expression avoids a lost update if two requests toggle the same row.
    # QuerySet.update bypasses auto_now, so update the timestamp explicitly.
    Task.objects.filter(pk=task.pk, owner=request.user).update(
        completed=~F("completed"), updated_at=timezone.now()
    )
    return redirect("tasks:list")
