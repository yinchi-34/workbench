import contextlib
import io
import json
import subprocess
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import merge  # noqa: E402


def fake_gh(view=None, checks_code=0, merge_code=0):
    """返回一个假的 gh：记录调用，按子命令给出预设结果。"""
    view = view or {"state": "OPEN", "isDraft": False, "title": "两数之和", "headRefName": "feat/two-sum"}
    calls = []

    def run(args):
        calls.append(list(args))
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
    return [c[1] for c in calls]


class MergeTest(unittest.TestCase):
    def merge(self, run, dry_run=False):
        with contextlib.redirect_stdout(io.StringIO()):
            merge.merge("12", None, dry_run, run)

    def test_merges_when_checks_pass(self):
        run, calls = fake_gh()
        self.merge(run)
        self.assertEqual(subcommands(calls), ["view", "checks", "merge"])
        self.assertIn("--squash", calls[-1])
        self.assertIn("--delete-branch", calls[-1])

    def test_refuses_when_checks_fail(self):
        run, calls = fake_gh(checks_code=1)
        with self.assertRaises(merge.MergeRefused):
            self.merge(run)
        self.assertNotIn("merge", subcommands(calls))

    def test_refuses_draft(self):
        run, calls = fake_gh(view={"state": "OPEN", "isDraft": True, "title": "t", "headRefName": "b"})
        with self.assertRaises(merge.MergeRefused):
            self.merge(run)
        self.assertEqual(subcommands(calls), ["view"])

    def test_refuses_closed(self):
        run, _ = fake_gh(view={"state": "MERGED", "isDraft": False, "title": "t", "headRefName": "b"})
        with self.assertRaises(merge.MergeRefused):
            self.merge(run)

    def test_dry_run_does_not_merge(self):
        run, calls = fake_gh()
        self.merge(run, dry_run=True)
        self.assertEqual(subcommands(calls), ["view", "checks"])

    def test_merge_failure_reported(self):
        run, _ = fake_gh(merge_code=1)
        with self.assertRaises(merge.MergeRefused):
            self.merge(run)

    def test_repo_flag_passed_through(self):
        run, calls = fake_gh()
        with contextlib.redirect_stdout(io.StringIO()):
            merge.merge("12", "yinchi-34/leetcode-go", False, run)
        for call in calls:
            self.assertIn("yinchi-34/leetcode-go", call)


if __name__ == "__main__":
    unittest.main()
