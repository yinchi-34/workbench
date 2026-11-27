#!/usr/bin/env python3
"""等 PR 的检查全部通过后再压缩合并并删除分支，否则拒绝合并。

私有仓库免费版没有分支保护，用这个脚本代替网页上的合并按钮（护栏第 3 层）。

用法（在业务仓库目录里，需要已登录的 gh）：

    python <workbench>/scripts/merge.py 12            # 等检查跑完，全部通过就合并
    python <workbench>/scripts/merge.py 12 --dry-run  # 只检查，不合并
    python <workbench>/scripts/merge.py 12 --allow-test-changes  # 已审阅被修改的测试，允许合并

PR 修改、删除或重命名已有测试文件时拒绝合并，除非指定 --allow-test-changes；新增测试文件不受影响。
该检查是对 fullstack 模板中 protect_tests.py 钩子的补充，用于覆盖钩子无法拦截的 Bash 修改。
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import PurePosixPath

# gh pr checks 的退出码：0 全部通过，8 还在运行（不加 --watch 时）。
CHECKS_PASSED = 0


# 测试文件的判断规则，与 templates/fullstack/.claude/hooks/protect_tests.py 保持一致。
TEST_DIRS = {"__tests__", "testdata"}
JS_EXTS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue"}


class MergeRefused(Exception):
    pass


def is_test_file(path: str) -> bool:
    p = PurePosixPath(path.replace("\\", "/"))
    name = p.name
    if TEST_DIRS & set(p.parts[:-1]):
        return True
    if name.endswith("_test.go"):
        return True
    if name.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py")):
        return True
    stem, ext = PurePosixPath(name).stem, PurePosixPath(name).suffix
    return ext in JS_EXTS and (stem.endswith(".test") or stem.endswith(".spec"))


def changed_tests(files: list[dict]) -> list[str]:
    """从 PR 文件列表（REST pulls/files 格式）中筛选出被修改、删除或重命名的已有测试文件。"""
    hits = []
    for f in files:
        status = f.get("status")
        if status == "added":
            continue
        old = f.get("previous_filename") or f["filename"]
        if is_test_file(f["filename"]) or is_test_file(old):
            hits.append(f"{f['filename']}（{status}）")
    return hits


Runner = Callable[[Sequence[str]], subprocess.CompletedProcess]


def run_gh(args: Sequence[str]) -> subprocess.CompletedProcess:
    # Windows 上 gh 可能是 .exe 以外的包装，用 which 找到完整路径。
    return subprocess.run([shutil.which("gh") or "gh", *args], text=True, capture_output=True)


def merge(pr: str, repo: str | None, dry_run: bool, run: Runner = run_gh, allow_test_changes: bool = False) -> None:
    repo_args = ["--repo", repo] if repo else []

    view = run(["pr", "view", pr, *repo_args, "--json", "number,state,isDraft,title,headRefName"])
    if view.returncode != 0:
        raise MergeRefused(f"找不到 PR {pr}：{view.stderr.strip()}")
    info = json.loads(view.stdout)
    if info["state"] != "OPEN":
        raise MergeRefused(f"PR {pr} 状态是 {info['state']}，不是 OPEN")
    if info["isDraft"]:
        raise MergeRefused(f"PR {pr} 还是草稿，先标记为 Ready for review")
    print(f"PR {pr}：{info['title']}（{info['headRefName']}）")

    # {owner}/{repo} 由 gh 替换为当前目录对应的仓库；--jq '.[]' 使分页结果每行输出一个对象。
    path = f"repos/{repo or '{owner}/{repo}'}/pulls/{info['number']}/files"
    files = run(["api", "--paginate", path, "--jq", ".[]"])
    if files.returncode != 0:
        raise MergeRefused(f"读取 PR 文件列表失败：{files.stderr.strip()}")
    tests = changed_tests([json.loads(line) for line in files.stdout.splitlines() if line.strip()])
    if tests:
        listing = "、".join(tests)
        if not allow_test_changes:
            raise MergeRefused(f"PR 修改了已有测试文件：{listing}。审阅后请加 --allow-test-changes 重新执行")
        print(f"已确认的测试文件改动：{listing}")

    print("等待检查结果……")
    checks = run(["pr", "checks", pr, *repo_args, "--watch", "--fail-fast"])
    print(checks.stdout, end="")
    if checks.returncode != CHECKS_PASSED:
        detail = checks.stderr.strip() or "有检查未通过"
        raise MergeRefused(f"检查未全部通过，拒绝合并：{detail}")

    if dry_run:
        print("[dry-run] 检查全部通过，将执行压缩合并并删除分支。")
        return
    result = run(["pr", "merge", pr, *repo_args, "--squash", "--delete-branch"])
    if result.returncode != 0:
        raise MergeRefused(f"合并失败：{result.stderr.strip()}")
    print(f"已压缩合并 PR {pr} 并删除分支 {info['headRefName']}。")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="检查全部通过后才合并 PR")
    parser.add_argument("pr", help="PR 编号或链接")
    parser.add_argument("--repo", help="owner/name，默认取当前目录的仓库")
    parser.add_argument("--dry-run", action="store_true", help="只检查，不合并")
    parser.add_argument("--allow-test-changes", action="store_true", help="已审阅被修改的测试文件，允许合并")
    args = parser.parse_args(argv)

    if shutil.which("gh") is None:
        print("错误：找不到 gh 命令，先安装并运行 gh auth login", file=sys.stderr)
        return 1
    try:
        merge(args.pr, args.repo, args.dry_run, allow_test_changes=args.allow_test_changes)
    except MergeRefused as e:
        print(f"错误：{e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
