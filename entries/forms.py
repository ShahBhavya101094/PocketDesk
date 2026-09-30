from django import forms

from .models import Entry
from .validators import DUPLICATE_KEY_MESSAGE, normalize_key, normalize_value


class EntryForm(forms.ModelForm):
    class Meta:
        model = Entry
        fields = ["key", "value"]
        widgets = {
            "key": forms.TextInput(attrs={"placeholder": "course_link", "autocapitalize": "none"}),
            "value": forms.Textarea(attrs={"rows": 6, "placeholder": "A useful link or note…"}),
        }
        help_texts = {
            "key": "1–80 letters, digits, underscores or hyphens; saved in lowercase.",
            "value": "Up to 5000 characters. Do not store passwords or sensitive secrets.",
        }

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user

    def clean_key(self):
        key = normalize_key(self.cleaned_data["key"])
        duplicates = Entry.objects.filter(owner=self.user, key=key)
        if self.instance.pk:
            duplicates = duplicates.exclude(pk=self.instance.pk)
        if duplicates.exists():
            raise forms.ValidationError(DUPLICATE_KEY_MESSAGE, code="unique")
        return key

    def clean_value(self):
        return normalize_value(self.cleaned_data["value"])
