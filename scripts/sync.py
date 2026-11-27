#!/usr/bin/env python3
"""把 workbench 里的基底层、技能和 MCP 配置分发到 Claude Code、Codex、pi。

用法（在 workbench 根目录，需要 Python 3.11 以上，只用标准库）：

    python scripts/sync.py            # 执行同步
    python scripts/sync.py --dry-run  # 只打印将要做的改动

能建符号链接就建链接，否则（例如 Windows 没开开发者模式）改为复制。
覆盖已有文件前先备份到 ~/.workbench-backup/<日期>/。重复运行结果不变。
"""

from __future__ import annotations

import argparse
import datetime
import filecmp
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path


class Syncer:
    def __init__(self, repo: Path, home: Path, dry_run: bool, backup_dir: Path | None = None):
        self.repo = repo
        self.home = home
        self.dry_run = dry_run
        self.backup_dir = backup_dir or home / ".workbench-backup" / datetime.date.today().isoformat()
        self.changed = 0

    def log(self, msg: str) -> None:
        print(("[dry-run] " if self.dry_run else "") + msg)

    def expand(self, path: str) -> Path:
        if path == "~":
            return self.home
        if path.startswith("~/"):
            return self.home / path[2:]
        return Path(path)

    def sync_all(self, cfg: dict) -> None:
        for t in cfg.get("links", []):
            self.place(self.repo / t["src"], self.expand(t["dst"]))

        for t in cfg.get("skills", []):
            for skill in self.list_skills():
                self.place(skill, self.expand(t["dst"]) / skill.name)

        if cfg.get("mcp"):
            servers = load_servers(self.repo / "mcp" / "servers.json")
            for t in cfg["mcp"]:
                self.sync_mcp(t, servers)

        self.log("全部已是最新，没有改动。" if self.changed == 0 else f"共 {self.changed} 处改动。")

    def list_skills(self) -> list[Path]:
        root = self.repo / "skills"
        if not root.is_dir():
            return []
        return sorted(p for p in root.iterdir() if (p / "SKILL.md").is_file())

    # ---- 链接或复制 ----

    def place(self, src: Path, dst: Path) -> None:
        """让 dst 指向 src。dst 已是指向 src 的链接，或内容相同的副本时不做任何事。"""
        if not src.exists():
            raise FileNotFoundError(src)

        if dst.is_symlink():
            if os.readlink(dst) == str(src):
                return
            # 旧链接本身不含数据，直接删掉重建。
            if not self.dry_run:
                dst.unlink()
        elif dst.exists():
            if same_content(src, dst):
                return
            self.backup(dst)

        self.changed += 1
        if self.dry_run:
            self.log(f"链接 {dst} -> {src}")
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            dst.symlink_to(src, target_is_directory=src.is_dir())
            self.log(f"链接 {dst} -> {src}")
        except OSError:
            copy_path(src, dst)
            self.log(f"复制 {src} -> {dst}（无法建链接）")

    def write_file(self, dst: Path, content: str) -> None:
        """写入生成的内容；已有文件内容不同时先备份。"""
        if dst.exists():
            if dst.read_text(encoding="utf-8") == content:
                return
            self.backup(dst)
        self.changed += 1
        self.log(f"写入 {dst}")
        if self.dry_run:
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(content, encoding="utf-8", newline="\n")

    def backup(self, path: Path) -> None:
        """把 path 移到备份目录，保留它相对主目录的路径。"""
        try:
            rel = path.relative_to(self.home)
        except ValueError:
            # 不在主目录下：用去掉盘符的绝对路径。
            rel = Path(*[p.replace(":", "") for p in path.parts if p not in ("/", "\\")])
        dst = self.backup_dir / rel
        self.log(f"备份 {path} -> {dst}")
        if self.dry_run:
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.exists() or dst.is_symlink():
            # 同一天已备份过：保留最早那份，当前这份直接删掉。
            remove_path(path)
            return
        shutil.move(str(path), str(dst))

    # ---- MCP ----

    def sync_mcp(self, t: dict, servers: dict) -> None:
        fmt = t["format"]
        if fmt == "codex-toml":
            path = self.expand(t["path"])
            old = path.read_text(encoding="utf-8") if path.exists() else ""
            self.write_file(path, merge_codex_toml(old, servers))
        elif fmt == "mcp-json":
            path = self.expand(t["path"])
            old = path.read_text(encoding="utf-8") if path.exists() else ""
            self.write_file(path, merge_mcp_json(old, servers))
        elif fmt == "claude-cli":
            self.sync_claude(self.expand(t["state"]), servers)
        else:
            raise ValueError(f"{t['tool']}：不支持的 MCP 格式 {fmt!r}")

    def sync_claude(self, state: Path, servers: dict) -> None:
        """用 claude mcp add-json --scope user 写入，不直接改 ~/.claude.json。"""
        current = {}
        if state.exists():
            current = json.loads(state.read_text(encoding="utf-8")).get("mcpServers", {})

        for name, srv in sorted(servers.items()):
            if current.get(name) == srv:
                continue
            self.changed += 1
            payload = json.dumps(srv, ensure_ascii=False)
            self.log(f"claude mcp add-json --scope user {name} {payload}")
            if self.dry_run:
                continue
            if shutil.which("claude") is None:
                self.log(f"警告：找不到 claude 命令，跳过 {name}")
                continue
            if name in current:
                self.claude("mcp", "remove", "--scope", "user", name)
            self.claude("mcp", "add-json", "--scope", "user", name, payload)

    def claude(self, *args: str) -> None:
        # 主目录与 --home 一致，保证写入的就是读取状态的那份配置。
        env = {**os.environ, "HOME": str(self.home), "USERPROFILE": str(self.home)}
        # Windows 上 claude 是 .cmd，需要用 which 找到完整路径。
        subprocess.run([shutil.which("claude") or "claude", *args], env=env, check=True)


# ---- 文件工具 ----


def same_content(a: Path, b: Path) -> bool:
    if a.is_dir() != b.is_dir():
        return False
    if a.is_file():
        return filecmp.cmp(a, b, shallow=False)
    files_a = sorted(p.relative_to(a) for p in a.rglob("*") if p.is_file())
    files_b = sorted(p.relative_to(b) for p in b.rglob("*") if p.is_file())
    return files_a == files_b and all(filecmp.cmp(a / f, b / f, shallow=False) for f in files_a)


def copy_path(src: Path, dst: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        shutil.copyfile(src, dst)


def remove_path(path: Path) -> None:
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    else:
        path.unlink()


# ---- MCP 格式转换 ----


def load_servers(path: Path) -> dict:
    """读取标准 mcpServers 格式。密钥只写成 ${VAR} 形式的环境变量引用。"""
    servers = json.loads(path.read_text(encoding="utf-8"))["mcpServers"]
    for name, srv in servers.items():
        if ("command" in srv) == ("url" in srv):
            raise ValueError(f"{path}：{name} 必须且只能有 command 或 url 之一")
    return servers


def merge_mcp_json(old: str, servers: dict) -> str:
    """pi-mcp-adapter 读取的标准格式：只替换同名条目，其他字段和服务器保留。"""
    doc = json.loads(old) if old.strip() else {}
    doc.setdefault("mcpServers", {}).update(servers)
    return json.dumps(doc, ensure_ascii=False, indent=2) + "\n"


HEADER_RE = re.compile(r"^\s*\[\[?\s*([^\]]+?)\s*\]\]?\s*(#.*)?$")
ENV_REF_RE = re.compile(r"^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$")
BEARER_REF_RE = re.compile(r"^Bearer \$\{([A-Za-z_][A-Za-z0-9_]*)\}$")


def merge_codex_toml(config: str, servers: dict) -> str:
    """删掉 config 里由 workbench 管理的 [mcp_servers.<名字>] 表（含子表），
    再把新生成的表追加到末尾；其他内容原样保留，包括注释。"""
    managed = set(servers) | {f'"{n}"' for n in servers}

    def is_managed(table: str) -> bool:
        if not table.startswith("mcp_servers."):
            return False
        rest = table[len("mcp_servers.") :]
        return any(rest == k or rest.startswith(k + ".") for k in managed)

    kept, skipping = [], False
    for line in config.split("\n"):
        m = HEADER_RE.match(line)
        if m:
            skipping = is_managed(m.group(1))
        if not skipping:
            kept.append(line)
    out = "\n".join(kept).rstrip("\n")
    return (out + "\n\n" if out else "") + render_codex(servers)


def render_codex(servers: dict) -> str:
    blocks = []
    for name, srv in sorted(servers.items()):
        lines = [f"[mcp_servers.{toml_key(name)}]"]
        if "command" in srv:
            lines.append(f"command = {toml_str(srv['command'])}")
            if srv.get("args"):
                lines.append(f"args = {toml_array(srv['args'])}")
            # 值是同名 ${VAR} 时让 Codex 从环境变量转发，其他值原样写入。
            env = srv.get("env", {})
            forward = sorted(k for k, v in env.items() if (m := ENV_REF_RE.match(v)) and m.group(1) == k)
            literal = {k: v for k, v in env.items() if k not in forward}
            if literal:
                lines.append(f"env = {toml_inline(literal)}")
            if forward:
                lines.append(f"env_vars = {toml_array(forward)}")
        else:
            lines.append(f"url = {toml_str(srv['url'])}")
            literal, from_env = {}, {}
            for k, v in srv.get("headers", {}).items():
                if k.lower() == "authorization" and (m := BEARER_REF_RE.match(v)):
                    lines.append(f"bearer_token_env_var = {toml_str(m.group(1))}")
                elif m := ENV_REF_RE.match(v):
                    from_env[k] = m.group(1)
                else:
                    literal[k] = v
            if literal:
                lines.append(f"http_headers = {toml_inline(literal)}")
            if from_env:
                lines.append(f"env_http_headers = {toml_inline(from_env)}")
        blocks.append("\n".join(lines) + "\n")
    return "\n".join(blocks)


def toml_str(s: str) -> str:
    # JSON 字符串转义与 TOML 基本字符串兼容。
    return json.dumps(s, ensure_ascii=False)


def toml_key(k: str) -> str:
    return k if re.fullmatch(r"[A-Za-z0-9_-]+", k) else toml_str(k)


def toml_array(items: list[str]) -> str:
    return "[" + ", ".join(toml_str(s) for s in items) + "]"


def toml_inline(d: dict) -> str:
    return "{ " + ", ".join(f"{toml_key(k)} = {toml_str(v)}" for k, v in sorted(d.items())) + " }"


# ---- 入口 ----


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="同步基底层、技能和 MCP 到各助手")
    parser.add_argument("--repo", default=Path(__file__).resolve().parent.parent, type=Path, help="workbench 根目录")
    parser.add_argument("--config", default="configs/targets.toml", help="同步目标配置，相对 --repo")
    parser.add_argument("--home", default=Path.home(), type=Path, help="用户主目录")
    parser.add_argument("--dry-run", action="store_true", help="只打印将要做的改动，不写入")
    args = parser.parse_args(argv)

    repo = args.repo.resolve()
    if not (repo / "base" / "AGENTS.md").is_file():
        print(f"错误：{repo} 不是 workbench 根目录（找不到 base/AGENTS.md）", file=sys.stderr)
        return 1
    with open(repo / args.config, "rb") as f:
        cfg = tomllib.load(f)

    try:
        Syncer(repo, args.home.resolve(), args.dry_run).sync_all(cfg)
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as e:
        print(f"错误：{e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
