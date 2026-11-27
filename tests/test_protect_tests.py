import importlib.util
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HOOK = ROOT / "templates/fullstack/.claude/hooks/protect_tests.py"

spec = importlib.util.spec_from_file_location("protect_tests", HOOK)
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)

sys.path.insert(0, str(ROOT / "scripts"))
import merge  # noqa: E402


def event(tool="Edit", path="server/message_test.go"):
    return {"tool_name": tool, "tool_input": {"file_path": path}, "cwd": "/repo"}


def exists(path, cwd):
    return True


def missing(path, cwd):
    return False


class DecideTest(unittest.TestCase):
    def test_blocks_editing_existing_test(self):
        self.assertIsNotNone(hook.decide(event(), exists))

    def test_blocks_overwriting_existing_test(self):
        self.assertIsNotNone(hook.decide(event("Write"), exists))
        self.assertIsNotNone(hook.decide(event("MultiEdit"), exists))

    def test_allows_new_test_file(self):
        self.assertIsNone(hook.decide(event("Write"), missing))

    def test_allows_non_test_file(self):
        self.assertIsNone(hook.decide(event(path="server/message.go"), exists))

    def test_ignores_other_tools(self):
        self.assertIsNone(hook.decide(event("Bash"), exists))

    def test_relative_path_resolved_against_cwd(self):
        seen = []
        hook.decide(event(path="a_test.go"), lambda p, cwd: seen.append((p, cwd)) or True)
        self.assertEqual(seen, [("a_test.go", "/repo")])


class ScriptTest(unittest.TestCase):
    """按 Claude Code 的调用方式跑脚本：stdin 进 JSON，stdout 出决定。"""

    def run_hook(self, payload):
        return subprocess.run(
            [sys.executable, str(HOOK)], input=payload, text=True, capture_output=True, check=True
        ).stdout

    def test_denies_with_json(self):
        out = json.loads(self.run_hook(json.dumps(event(path=__file__))))
        self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_silent_when_allowed(self):
        self.assertEqual(self.run_hook(json.dumps(event(path="/no/such/dir/x_test.go"))), "")

    def test_bad_input_allows(self):
        self.assertEqual(self.run_hook("not json"), "")


class SameRulesTest(unittest.TestCase):
    """钩子和 merge.py 各有一份 is_test_file，判断结果必须一致。"""

    def test_rules_match(self):
        paths = [
            "a_test.go",
            "a.go",
            "test_a.py",
            "a_test.py",
            "a.py",
            "a.spec.ts",
            "a.test.vue",
            "spec.ts",
            "__tests__/a.ts",
            "testdata/x",
            "docs/specs/a.md",
        ]
        for p in paths:
            with self.subTest(path=p):
                self.assertEqual(hook.is_test_file(p), merge.is_test_file(p))


if __name__ == "__main__":
    unittest.main()
