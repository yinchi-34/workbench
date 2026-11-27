#!/usr/bin/env python3
"""PreToolUse 钩子：禁止 agent 修改已有的测试文件，允许新建测试文件。

规划者需要编写新测试，因此不限制新建；放宽断言、删除用例等行为必然涉及已有文件，由本钩子拒绝。
已有测试如需修改，由开发者本人操作，或经开发者确认后临时停用本钩子。

仅拦截 Edit / Write / MultiEdit。通过 Bash（如 sed -i）进行的修改无法拦截，由 workbench 的 merge.py 在合并时检查。
测试文件的判断规则与 workbench/scripts/merge.py 中的 is_test_file 保持一致。
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
        f"{path} 为已有测试文件。测试是验收标准，agent 不得修改；如认为测试有误，请在报告首行写明“需要确认”并说明理由。"
    )


def _exists(path: str, cwd: str) -> bool:
    p = Path(path)
    return (p if p.is_absolute() else Path(cwd) / p).exists()


def main() -> int:
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0  # 输入无法解析时放行，避免钩子自身的问题阻塞正常工作
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
