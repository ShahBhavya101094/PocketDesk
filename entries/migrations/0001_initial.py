import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

import entries.validators


class Migration(migrations.Migration):
    initial = True
    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(
            name="Entry",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "key",
                    models.CharField(max_length=80, validators=[entries.validators.validate_key]),
                ),
                (
                    "value",
                    models.TextField(
                        max_length=5000, validators=[entries.validators.validate_value]
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "owner",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="entries",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["key", "id"],
                "constraints": [
                    models.UniqueConstraint(fields=("owner", "key"), name="unique_entry_owner_key")
                ],
            },
        ),
    ]
