import contextlib
import io
import json
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import sync  # noqa: E402

TARGETS = """
[[links]]
tool = "claude"
src = "base/AGENTS.md"
dst = "~/.claude/AGENTS.md"

[[skills]]
tool = "claude"
dst = "~/.claude/skills"

[[mcp]]
tool = "codex"
format = "codex-toml"
path = "~/.codex/config.toml"

[[mcp]]
tool = "pi"
format = "mcp-json"
path = "~/.config/mcp/mcp.json"
"""

CONTEXT7 = {"context7": {"type": "http", "url": "https://mcp.context7.com/mcp"}}


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class SyncTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name, "repo")
        self.home = Path(tmp.name, "home")
        self.home.mkdir()
        files = {
            "base/AGENTS.md": "# 基底层\n",
            "skills/code-review/SKILL.md": "---\nname: code-review\n---\n",
            "skills/code-review/ref/a.md": "a\n",
            "skills/not-a-skill/x.txt": "x\n",
            "mcp/servers.json": json.dumps({"mcpServers": CONTEXT7}),
        }
        for name, content in files.items():
            write(self.repo / name, content)

    def run_sync(self, dry_run=False) -> tuple[sync.Syncer, str]:
        s = sync.Syncer(self.repo, self.home, dry_run, self.home / ".workbench-backup" / "today")
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            s.sync_all(tomllib.loads(TARGETS))
        return s, out.getvalue()

    def test_idempotent(self):
        first, _ = self.run_sync()
        self.assertGreater(first.changed, 0)
        second, out = self.run_sync()
        self.assertEqual(second.changed, 0, out)

        self.assertEqual((self.home / ".claude/AGENTS.md").read_text(encoding="utf-8"), "# 基底层\n")
        self.assertEqual((self.home / ".claude/skills/code-review/ref/a.md").read_text(), "a\n")
        self.assertFalse((self.home / ".claude/skills/not-a-skill").exists(), "没有 SKILL.md 的目录不应同步")

    def test_dry_run_writes_nothing(self):
        s, out = self.run_sync(dry_run=True)
        self.assertGreater(s.changed, 0)
        self.assertIn("[dry-run]", out)
        self.assertEqual(list(self.home.iterdir()), [])

    def test_existing_file_backed_up(self):
        write(self.home / ".claude/AGENTS.md", "旧内容\n")
        self.run_sync()
        backup = self.home / ".workbench-backup/today/.claude/AGENTS.md"
        self.assertEqual(backup.read_text(encoding="utf-8"), "旧内容\n")
        self.assertEqual((self.home / ".claude/AGENTS.md").read_text(encoding="utf-8"), "# 基底层\n")

    def test_identical_copy_left_alone(self):
        # 模拟 Windows 上之前因无法建链接而复制过来的副本。
        write(self.home / ".claude/AGENTS.md", "# 基底层\n")
        self.run_sync()
        self.assertFalse((self.home / ".claude/AGENTS.md").is_symlink())
        self.assertFalse((self.home / ".workbench-backup").exists())


class CodexTomlTest(unittest.TestCase):
    def test_merge_replaces_only_managed_tables(self):
        old = """model = "gpt-5"

[mcp_servers.context7]
command = "npx"
args = ["-y", "old"]

[mcp_servers.context7.env]
KEY = "v"

[mcp_servers.other]
command = "other"

# 注释保留
[profiles.fast]
model = "mini"
"""
        got = sync.merge_codex_toml(old, CONTEXT7)
        for want in [
            'model = "gpt-5"',
            "[mcp_servers.other]",
            "# 注释保留",
            "[profiles.fast]",
            'url = "https://mcp.context7.com/mcp"',
        ]:
            self.assertIn(want, got)
        for gone in ['"old"', "[mcp_servers.context7.env]", "npx"]:
            self.assertNotIn(gone, got)
        self.assertEqual(sync.merge_codex_toml(got, CONTEXT7), got, "重复合并结果应不变")
        tomllib.loads(got)  # 生成的是合法 TOML

    def test_env_refs(self):
        servers = {
            "local": {"command": "npx", "args": ["-y", "pkg"], "env": {"TOKEN": "${TOKEN}", "MODE": "dev"}},
            "remote": {
                "url": "https://example.com/mcp",
                "headers": {"Authorization": "Bearer ${API_KEY}", "X-Key": "${X_KEY}", "X-Fixed": "1"},
            },
        }
        got = sync.render_codex(servers)
        for want in [
            'args = ["-y", "pkg"]',
            'env = { MODE = "dev" }',
            'env_vars = ["TOKEN"]',
            'bearer_token_env_var = "API_KEY"',
            'env_http_headers = { X-Key = "X_KEY" }',
            'http_headers = { X-Fixed = "1" }',
        ]:
            self.assertIn(want, got)
        tomllib.loads(got)


class McpJsonTest(unittest.TestCase):
    def test_keeps_other_servers(self):
        old = json.dumps(
            {"settings": {"x": 1}, "mcpServers": {"mine": {"command": "foo"}, "context7": {"command": "stale"}}}
        )
        doc = json.loads(sync.merge_mcp_json(old, CONTEXT7))
        self.assertEqual(doc["settings"], {"x": 1})
        self.assertEqual(doc["mcpServers"]["mine"], {"command": "foo"})
        self.assertEqual(doc["mcpServers"]["context7"], CONTEXT7["context7"])

    def test_rejects_ambiguous_server(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d, "servers.json")
            path.write_text('{"mcpServers":{"bad":{"command":"x","url":"https://x"}}}')
            with self.assertRaises(ValueError):
                sync.load_servers(path)


if __name__ == "__main__":
    unittest.main()
