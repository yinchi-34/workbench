import contextlib
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import merge  # noqa: E402


def fake_gh(view=None, checks_code=0, merge_code=0, files=None):
    """返回一个假的 gh：记录调用，按子命令给出预设结果。files 是 PR 文件列表（REST 格式）。"""
    view = view or {"number": 12, "state": "OPEN", "isDraft": False, "title": "两数之和", "headRefName": "feat/two-sum"}
    files = files if files is not None else [{"filename": "solution.go", "status": "modified"}]
    calls = []

    def run(args):
        calls.append(list(args))
        if args[0] == "api":
            return subprocess.CompletedProcess(args, 0, "".join(json.dumps(f) + "\n" for f in files), "")
        sub = args[1]
        if sub == "view":
            return subprocess.CompletedProcess(args, 0, json.dumps(view), "")
        if sub == "checks":
            return subprocess.CompletedProcess(args, checks_code, "test  pass\n", "" if checks_code == 0 else "fail")
        if sub == "merge":
            return subprocess.CompletedProcess(args, merge_code, "", "" if merge_code == 0 else "conflict")
        raise AssertionError(f"意外的 gh 调用：{args}")

    return run, calls


def subcommands(calls):
    return ["api" if c[0] == "api" else c[1] for c in calls]


class MergeTest(unittest.TestCase):
    def merge(self, run, dry_run=False, allow_test_changes=False):
        with contextlib.redirect_stdout(io.StringIO()):
            merge.merge("12", None, dry_run, run, allow_test_changes=allow_test_changes)

    def test_merges_when_checks_pass(self):
        run, calls = fake_gh()
        self.merge(run)
        self.assertEqual(subcommands(calls), ["view", "api", "checks", "merge"])
        self.assertIn("--squash", calls[-1])
        self.assertIn("--delete-branch", calls[-1])

    def test_refuses_when_checks_fail(self):
        run, calls = fake_gh(checks_code=1)
        with self.assertRaises(merge.MergeRefused):
            self.merge(run)
        self.assertNotIn("merge", subcommands(calls))

    def test_refuses_draft(self):
        run, calls = fake_gh(view={"number": 12, "state": "OPEN", "isDraft": True, "title": "t", "headRefName": "b"})
        with self.assertRaises(merge.MergeRefused):
            self.merge(run)
        self.assertEqual(subcommands(calls), ["view"])

    def test_refuses_closed(self):
        run, _ = fake_gh(view={"number": 12, "state": "MERGED", "isDraft": False, "title": "t", "headRefName": "b"})
        with self.assertRaises(merge.MergeRefused):
            self.merge(run)

    def test_dry_run_does_not_merge(self):
        run, calls = fake_gh()
        self.merge(run, dry_run=True)
        self.assertEqual(subcommands(calls), ["view", "api", "checks"])

    def test_merge_failure_reported(self):
        run, _ = fake_gh(merge_code=1)
        with self.assertRaises(merge.MergeRefused):
            self.merge(run)

    def test_repo_flag_passed_through(self):
        run, calls = fake_gh()
        with contextlib.redirect_stdout(io.StringIO()):
            merge.merge("12", "yinchi-34/leetcode-go", False, run)
        for call in calls:
            self.assertTrue(any("yinchi-34/leetcode-go" in arg for arg in call), call)

    # ---- 测试文件改动检查 ----

    def test_refuses_modified_test_file(self):
        run, calls = fake_gh(files=[{"filename": "web/src/quote.spec.ts", "status": "modified"}])
        with self.assertRaises(merge.MergeRefused) as cm:
            self.merge(run)
        self.assertIn("quote.spec.ts", str(cm.exception))
        self.assertNotIn("checks", subcommands(calls), "测试被改时不必再等 CI")

    def test_refuses_removed_test_file(self):
        run, _ = fake_gh(files=[{"filename": "server/message_test.go", "status": "removed"}])
        with self.assertRaises(merge.MergeRefused):
            self.merge(run)

    def test_refuses_test_renamed_away(self):
        files = [
            {"filename": "server/message.go.bak", "previous_filename": "server/message_test.go", "status": "renamed"}
        ]
        run, _ = fake_gh(files=files)
        with self.assertRaises(merge.MergeRefused):
            self.merge(run)

    def test_added_test_file_is_fine(self):
        run, calls = fake_gh(files=[{"filename": "server/quote_test.go", "status": "added"}])
        self.merge(run)
        self.assertIn("merge", subcommands(calls))

    def test_allow_flag_merges_test_changes(self):
        run, calls = fake_gh(files=[{"filename": "server/message_test.go", "status": "modified"}])
        self.merge(run, allow_test_changes=True)
        self.assertIn("merge", subcommands(calls))

    def test_api_failure_refuses(self):
        def run(args):
            if args[0] == "api":
                return subprocess.CompletedProcess(args, 1, "", "HTTP 404")
            return fake_gh()[0](args)

        with self.assertRaises(merge.MergeRefused):
            self.merge(run)


class IsTestFileTest(unittest.TestCase):
    def test_patterns(self):
        cases = {
            "server/message_test.go": True,
            "server/message.go": False,
            "tests/test_merge.py": True,
            "pkg/merge_test.py": True,
            "scripts/merge.py": False,
            "web/src/Quote.spec.ts": True,
            "web/src/quote.test.tsx": True,
            "web/src/__tests__/quote.ts": True,
            "server/testdata/big.json": True,
            "web/src/spec.ts": False,
            "docs/specs/quote.md": False,
            "web\\src\\quote.test.js": True,
        }
        for path, want in cases.items():
            with self.subTest(path=path):
                self.assertEqual(merge.is_test_file(path), want)


if __name__ == "__main__":
    unittest.main()
