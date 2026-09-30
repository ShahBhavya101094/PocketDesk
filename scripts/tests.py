"""No database is needed to verify the local bootstrap safety contract."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.init_local import initialize


class LocalInitializationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        (self.root / ".env.example").write_text(
            "DEBUG=True\nDJANGO_SECRET_KEY=replace-with-a-new-random-secret\n",
            encoding="utf-8",
        )

    @patch.dict(os.environ, {"VERCEL": "0"})
    def test_creates_private_random_secret(self):
        self.assertTrue(initialize(self.root))
        content = (self.root / ".env").read_text(encoding="utf-8")
        self.assertNotIn("replace-with", content)
        self.assertGreater(len(content.split("DJANGO_SECRET_KEY=")[1].strip()), 50)
        if os.name != "nt":
            self.assertEqual((self.root / ".env").stat().st_mode & 0o777, 0o600)

    @patch.dict(os.environ, {"VERCEL": "0"})
    def test_preserves_existing_environment(self):
        (self.root / ".env").write_text("keep-existing", encoding="utf-8")
        self.assertFalse(initialize(self.root))
        self.assertEqual((self.root / ".env").read_text(encoding="utf-8"), "keep-existing")

    @patch.dict(os.environ, {"VERCEL": "1"})
    def test_refuses_vercel(self):
        with self.assertRaises(RuntimeError):
            initialize(self.root)
        self.assertFalse((self.root / ".env").exists())
