// sync 把 workbench 里的基底层、技能和 MCP 配置分发到 Claude Code、Codex、pi。
//
// 用法（在 workbench 根目录）：
//
//	go run ./scripts/sync            # 执行同步
//	go run ./scripts/sync -dry-run   # 只打印将要做的改动
//
// 能建符号链接就建链接，否则（例如 Windows 没开开发者模式）改为复制。
// 覆盖已有文件前先备份到 ~/.workbench-backup/<日期>/。重复运行结果不变。
package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"time"
)

func main() {
	repo := flag.String("repo", ".", "workbench 根目录")
	config := flag.String("config", "configs/targets.toml", "同步目标配置，相对 -repo")
	dryRun := flag.Bool("dry-run", false, "只打印将要做的改动，不写入")
	home := flag.String("home", "", "用户主目录，默认取当前用户的")
	flag.Parse()

	if err := run(*repo, *config, *home, *dryRun); err != nil {
		fmt.Fprintln(os.Stderr, "错误：", err)
		os.Exit(1)
	}
}

func run(repo, config, home string, dryRun bool) error {
	repo, err := filepath.Abs(repo)
	if err != nil {
		return err
	}
	if _, err := os.Stat(filepath.Join(repo, "base", "AGENTS.md")); err != nil {
		return fmt.Errorf("%s 不是 workbench 根目录（找不到 base/AGENTS.md）", repo)
	}
	if home == "" {
		if home, err = os.UserHomeDir(); err != nil {
			return err
		}
	}
	cfg, err := loadConfig(filepath.Join(repo, config))
	if err != nil {
		return err
	}

	s := &syncer{
		repo:      repo,
		home:      home,
		dryRun:    dryRun,
		backupDir: filepath.Join(home, ".workbench-backup", time.Now().Format("2006-01-02")),
		out:       os.Stdout,
	}
	return s.syncAll(cfg)
}
