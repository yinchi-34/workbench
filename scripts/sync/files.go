package main

import (
	"bytes"
	"fmt"
	"io"
	"io/fs"
	"os"
	"path/filepath"
	"strings"
)

type syncer struct {
	repo      string
	home      string
	dryRun    bool
	backupDir string
	out       io.Writer

	changed int
}

func (s *syncer) logf(format string, args ...any) {
	prefix := ""
	if s.dryRun {
		prefix = "[dry-run] "
	}
	_, _ = fmt.Fprintf(s.out, prefix+format+"\n", args...)
}

func (s *syncer) syncAll(cfg *config) error {
	for _, l := range cfg.Links {
		src := filepath.Join(s.repo, filepath.FromSlash(l.Src))
		if err := s.place(src, expand(l.Dst, s.home)); err != nil {
			return fmt.Errorf("%s：%w", l.Tool, err)
		}
	}

	skills, err := s.listSkills()
	if err != nil {
		return err
	}
	for _, t := range cfg.Skills {
		dir := expand(t.Dst, s.home)
		for _, name := range skills {
			src := filepath.Join(s.repo, "skills", name)
			if err := s.place(src, filepath.Join(dir, name)); err != nil {
				return fmt.Errorf("%s 技能 %s：%w", t.Tool, name, err)
			}
		}
	}

	if len(cfg.MCP) > 0 {
		servers, err := loadServers(filepath.Join(s.repo, "mcp", "servers.json"))
		if err != nil {
			return err
		}
		for _, t := range cfg.MCP {
			if err := s.syncMCP(t, servers); err != nil {
				return fmt.Errorf("%s MCP：%w", t.Tool, err)
			}
		}
	}

	if s.changed == 0 {
		s.logf("全部已是最新，没有改动。")
	} else {
		s.logf("共 %d 处改动。", s.changed)
	}
	return nil
}

// listSkills 返回 skills/ 下含 SKILL.md 的目录名。
func (s *syncer) listSkills() ([]string, error) {
	entries, err := os.ReadDir(filepath.Join(s.repo, "skills"))
	if os.IsNotExist(err) {
		return nil, nil
	}
	if err != nil {
		return nil, err
	}
	var names []string
	for _, e := range entries {
		if !e.IsDir() {
			continue
		}
		if _, err := os.Stat(filepath.Join(s.repo, "skills", e.Name(), "SKILL.md")); err == nil {
			names = append(names, e.Name())
		}
	}
	return names, nil
}

// place 让 dst 指向 src：优先建符号链接，失败时复制。
// dst 已是指向 src 的链接，或内容与 src 相同的副本时不做任何事。
func (s *syncer) place(src, dst string) error {
	if _, err := os.Stat(src); err != nil {
		return err
	}

	if info, err := os.Lstat(dst); err == nil {
		if info.Mode()&fs.ModeSymlink != 0 {
			if target, _ := os.Readlink(dst); target == src {
				return nil
			}
			// 旧链接本身不含数据，直接删掉重建。
			if !s.dryRun {
				if err := os.Remove(dst); err != nil {
					return err
				}
			}
		} else {
			same, err := sameContent(src, dst)
			if err != nil {
				return err
			}
			if same {
				return nil
			}
			if err := s.backup(dst); err != nil {
				return err
			}
		}
	} else if !os.IsNotExist(err) {
		return err
	}

	s.changed++
	if s.dryRun {
		s.logf("链接 %s -> %s", dst, src)
		return nil
	}
	if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
		return err
	}
	if err := os.Symlink(src, dst); err == nil {
		s.logf("链接 %s -> %s", dst, src)
		return nil
	}
	if err := copyPath(src, dst); err != nil {
		return err
	}
	s.logf("复制 %s -> %s（无法建链接）", src, dst)
	return nil
}

// writeFile 写入生成的内容；已有文件内容不同时先备份。
func (s *syncer) writeFile(dst string, content []byte) error {
	old, err := os.ReadFile(dst)
	switch {
	case err == nil && bytes.Equal(old, content):
		return nil
	case err == nil:
		if err := s.backup(dst); err != nil {
			return err
		}
	case !os.IsNotExist(err):
		return err
	}

	s.changed++
	s.logf("写入 %s", dst)
	if s.dryRun {
		return nil
	}
	if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
		return err
	}
	return os.WriteFile(dst, content, 0o644)
}

// backup 把 path 移到备份目录，保留它相对主目录的路径。
func (s *syncer) backup(path string) error {
	rel, err := filepath.Rel(s.home, path)
	if err != nil || strings.HasPrefix(rel, "..") {
		// 不在主目录下：用去掉盘符和分隔符的绝对路径。
		rel = strings.TrimLeft(strings.ReplaceAll(filepath.ToSlash(path), ":", ""), "/")
	}
	dst := filepath.Join(s.backupDir, rel)
	s.logf("备份 %s -> %s", path, dst)
	if s.dryRun {
		return nil
	}
	if err := os.MkdirAll(filepath.Dir(dst), 0o755); err != nil {
		return err
	}
	if _, err := os.Lstat(dst); err == nil {
		// 同一天已备份过：保留最早那份，当前这份直接替换掉。
		return os.RemoveAll(path)
	}
	if err := os.Rename(path, dst); err == nil {
		return nil
	}
	// 跨盘无法 rename 时复制后删除。
	if err := copyPath(path, dst); err != nil {
		return err
	}
	return os.RemoveAll(path)
}

func copyPath(src, dst string) error {
	return filepath.WalkDir(src, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		rel, err := filepath.Rel(src, path)
		if err != nil {
			return err
		}
		target := filepath.Join(dst, rel)
		if d.IsDir() {
			return os.MkdirAll(target, 0o755)
		}
		data, err := os.ReadFile(path)
		if err != nil {
			return err
		}
		if err := os.MkdirAll(filepath.Dir(target), 0o755); err != nil {
			return err
		}
		return os.WriteFile(target, data, 0o644)
	})
}

// sameContent 比较两个文件或两棵目录树的内容是否完全相同。
func sameContent(a, b string) (bool, error) {
	ia, err := os.Stat(a)
	if err != nil {
		return false, err
	}
	ib, err := os.Stat(b)
	if err != nil {
		return false, err
	}
	if ia.IsDir() != ib.IsDir() {
		return false, nil
	}
	if !ia.IsDir() {
		da, err := os.ReadFile(a)
		if err != nil {
			return false, err
		}
		db, err := os.ReadFile(b)
		if err != nil {
			return false, err
		}
		return bytes.Equal(da, db), nil
	}

	fa, err := listFiles(a)
	if err != nil {
		return false, err
	}
	fb, err := listFiles(b)
	if err != nil {
		return false, err
	}
	if len(fa) != len(fb) {
		return false, nil
	}
	for i := range fa {
		if fa[i] != fb[i] {
			return false, nil
		}
		same, err := sameContent(filepath.Join(a, fa[i]), filepath.Join(b, fb[i]))
		if err != nil || !same {
			return false, err
		}
	}
	return true, nil
}

func listFiles(root string) ([]string, error) {
	var files []string
	err := filepath.WalkDir(root, func(path string, d fs.DirEntry, err error) error {
		if err != nil || d.IsDir() {
			return err
		}
		rel, err := filepath.Rel(root, path)
		files = append(files, rel)
		return err
	})
	return files, err
}
