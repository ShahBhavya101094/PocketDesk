from django import forms

from .models import Task
from .validators import normalize_title


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        # Never accept owner from a browser. The view assigns request.user.
        fields = ["title", "completed"]
        widgets = {"title": forms.TextInput(attrs={"placeholder": "Prepare Django demo"})}
        help_texts = {"title": "3–200 characters. Keep the next action clear."}

    def clean_title(self):
        return normalize_title(self.cleaned_data["title"])
