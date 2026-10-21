#!/usr/bin/env python3
"""新电脑初始化：检查工具是否装好、安装 ccusage、给 Claude Code 配置用量状态栏。

用法（在 workbench 根目录）：

    python scripts/bootstrap.py            # 检查并初始化
    python scripts/bootstrap.py --dry-run  # 只打印将要做的改动

Windows、WSL、Linux 各跑一次。跑完再运行 scripts/sync.py 分发规则和技能。
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

from sync import Syncer

# (命令, 用途, 安装提示)
TOOLS = [
    ("git", "版本管理", "https://git-scm.com"),
    ("gh", "GitHub 操作、merge.py", "winget install GitHub.cli"),
    ("go", "leetcode-go", "https://go.dev/dl"),
    ("node", "pi、ccusage", "https://nodejs.org"),
    ("lefthook", "本地钩子", "winget install evilmartians.lefthook"),
    ("golangci-lint", "Go 代码检查", "https://golangci-lint.run/welcome/install/"),
    ("gitleaks", "密钥泄露检查", "winget install Gitleaks.Gitleaks"),
    ("claude", "Claude Code", "https://docs.claude.com/claude-code"),
    ("codex", "Codex", "npm install -g @openai/codex"),
    ("pi", "pi", "npm install -g @mariozechner/pi-coding-agent"),
]

STATUS_LINE = {"type": "command", "command": "ccusage statusline", "padding": 0}


def check_tools() -> list[str]:
    missing = []
    for cmd, purpose, hint in TOOLS:
        if shutil.which(cmd):
            print(f"  ✓ {cmd:<14} {purpose}")
        else:
            print(f"  ✗ {cmd:<14} {purpose}　安装：{hint}")
            missing.append(cmd)
    return missing


def install_ccusage(dry_run: bool) -> None:
    if shutil.which("ccusage"):
        print("ccusage 已安装。")
        return
    npm = shutil.which("npm")
    if npm is None:
        print("警告：找不到 npm，先装 Node.js 再重跑以安装 ccusage。")
        return
    print(("[dry-run] " if dry_run else "") + "npm install -g ccusage")
    if not dry_run:
        subprocess.run([npm, "install", "-g", "ccusage"], check=True)


def configure_status_line(s: Syncer, force: bool) -> None:
    """在 ~/.claude/settings.json 里加 statusLine，其他设置保留。"""
    path = s.home / ".claude" / "settings.json"
    settings = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    current = settings.get("statusLine")
    if current == STATUS_LINE:
        return
    if current is not None and not force:
        print(f"Claude Code 已有自定义状态栏 {json.dumps(current, ensure_ascii=False)}，保留不动；要替换加 --force。")
        return
    settings["statusLine"] = STATUS_LINE
    s.write_file(path, json.dumps(settings, ensure_ascii=False, indent=2) + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="新电脑初始化")
    parser.add_argument("--home", default=Path.home(), type=Path, help="用户主目录")
    parser.add_argument("--dry-run", action="store_true", help="只打印将要做的改动，不写入")
    parser.add_argument("--force", action="store_true", help="替换已有的自定义状态栏")
    args = parser.parse_args(argv)

    print("工具检查：")
    missing = check_tools()

    s = Syncer(Path(__file__).resolve().parent.parent, args.home.resolve(), args.dry_run)
    try:
        install_ccusage(args.dry_run)
        configure_status_line(s, args.force)
    except (OSError, ValueError, subprocess.CalledProcessError) as e:
        print(f"错误：{e}", file=sys.stderr)
        return 1

    if missing:
        print(f"还缺 {len(missing)} 个工具：{', '.join(missing)}。装好后重跑本脚本。")
    else:
        print("工具齐全。下一步：python scripts/sync.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
