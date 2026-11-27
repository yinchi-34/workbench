#!/usr/bin/env python3
"""PreToolUse 钩子：不让 agent 修改已经存在的测试文件，新建测试文件放行。

规划者要写新测试，所以新建放行；执行者想放宽断言、删掉用例，改的一定是已有文件，这里拦下。
要改已有测试，由人自己改，或者人确认后临时关掉钩子。

只拦 Edit / Write / MultiEdit。用 Bash（sed -i 之类）改测试拦不住，由 workbench 的 merge.py 在合并时兜底。
测试文件的判断规则和 workbench/scripts/merge.py 的 is_test_file 保持一致。
"""

from __future__ import annotations

import json
import sys
from pathlib import Path, PurePosixPath

TEST_DIRS = {"__tests__", "testdata"}
JS_EXTS = {".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".vue"}


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


def decide(event: dict, exists) -> str | None:
    """返回拒绝理由；放行时返回 None。exists 用来判断文件是否已存在，方便测试替换。"""
    if event.get("tool_name") not in {"Edit", "Write", "MultiEdit"}:
        return None
    path = (event.get("tool_input") or {}).get("file_path") or ""
    if not path or not is_test_file(path):
        return None
    if not exists(path, event.get("cwd") or "."):
        return None
    return (
        f"{path} 是已有的测试文件，测试是验收标准，agent 不能改。认为测试写错了，在报告第一行写“需要确认”并说明理由。"
    )


def _exists(path: str, cwd: str) -> bool:
    p = Path(path)
    return (p if p.is_absolute() else Path(cwd) / p).exists()


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0  # 读不懂输入时放行，不因钩子自身问题卡住工作
    reason = decide(event, _exists)
    if reason:
        out = {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": reason,
            }
        }
        print(json.dumps(out, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
