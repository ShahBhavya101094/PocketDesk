from django.conf import settings
from django.db import models

from .validators import validate_title


class Task(models.Model):
    title = models.CharField(max_length=200, validators=[validate_title])
    completed = models.BooleanField(default=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tasks"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["completed", "id"]
        indexes = [models.Index(fields=["owner", "completed"], name="task_owner_status_idx")]

    def clean(self):
        # Forms call model validation; shell/service code must call full_clean()
        # before save(). Django intentionally does not validate on every save.
        super().clean()
        # Field validators enforce the rule. This hook only canonicalizes text,
        # so a ModelForm does not repeat an already-reported field error.
        if isinstance(self.title, str):
            self.title = self.title.strip()

    def __str__(self):
        return self.title
