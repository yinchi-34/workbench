import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import bootstrap  # noqa: E402
from sync import Syncer  # noqa: E402


class StatusLineTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.home = Path(tmp.name)
        self.settings = self.home / ".claude" / "settings.json"

    def configure(self, force=False, dry_run=False) -> Syncer:
        s = Syncer(Path("."), self.home, dry_run, self.home / "backup")
        with contextlib.redirect_stdout(io.StringIO()):
            bootstrap.configure_status_line(s, force)
        return s

    def write_settings(self, data):
        self.settings.parent.mkdir(parents=True)
        self.settings.write_text(json.dumps(data), encoding="utf-8")

    def read_settings(self):
        return json.loads(self.settings.read_text(encoding="utf-8"))

    def test_adds_status_line_and_keeps_other_settings(self):
        self.write_settings({"model": "opus", "permissions": {"allow": ["Bash(go test:*)"]}})
        self.configure()
        got = self.read_settings()
        self.assertEqual(got["statusLine"], bootstrap.STATUS_LINE)
        self.assertEqual(got["model"], "opus")
        self.assertEqual(got["permissions"], {"allow": ["Bash(go test:*)"]})

    def test_creates_settings_when_missing(self):
        self.configure()
        self.assertEqual(self.read_settings(), {"statusLine": bootstrap.STATUS_LINE})

    def test_idempotent(self):
        self.configure()
        self.assertEqual(self.configure().changed, 0)

    def test_keeps_custom_status_line_without_force(self):
        custom = {"type": "command", "command": "my-status"}
        self.write_settings({"statusLine": custom})
        self.configure()
        self.assertEqual(self.read_settings()["statusLine"], custom)

    def test_force_replaces_custom_status_line(self):
        self.write_settings({"statusLine": {"type": "command", "command": "my-status"}})
        self.configure(force=True)
        self.assertEqual(self.read_settings()["statusLine"], bootstrap.STATUS_LINE)

    def test_dry_run_writes_nothing(self):
        self.configure(dry_run=True)
        self.assertFalse(self.settings.exists())


if __name__ == "__main__":
    unittest.main()
