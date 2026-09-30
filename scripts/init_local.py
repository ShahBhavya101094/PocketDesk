"""Create a private local .env once, without displaying its generated secret.

Run before importing Django settings: python scripts/init_local.py
This helper never touches a production environment or overwrites an existing file.
"""

import os
import secrets
from pathlib import Path


def initialize(project_dir: Path) -> bool:
    """Return True when created, False when an existing .env is preserved."""
    if os.environ.get("VERCEL") == "1":
        raise RuntimeError("Local initialization is not available on Vercel.")
    target = project_dir / ".env"
    template = (project_dir / ".env.example").read_text(encoding="utf-8")
    marker = "replace-with-a-new-random-secret"
    if marker not in template:
        raise ValueError("The local template is missing its secret-key placeholder.")
    content = template.replace(marker, secrets.token_urlsafe(50))
    try:
        # Exclusive creation avoids accidental replacement, including concurrent runs.
        descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError:
        return False
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        output.write(content)
    return True


if __name__ == "__main__":
    created = initialize(Path(__file__).resolve().parent.parent)
    print(
        "Created private .env for local development."
        if created
        else "Kept existing .env unchanged."
    )
