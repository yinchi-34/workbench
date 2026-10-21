package main

import (
	"bytes"
	"encoding/json"
	"os"
	"path/filepath"
	"strings"
	"testing"
)

// newRepo 在临时目录里建一个最小的 workbench。
func newRepo(t *testing.T) string {
	t.Helper()
	repo := t.TempDir()
	files := map[string]string{
		"base/AGENTS.md":           "# 基底层\n",
		"base/CLAUDE.md":           "@AGENTS.md\n",
		"skills/coding/SKILL.md":   "---\nname: coding\n---\n",
		"skills/coding/ref/a.md":   "a\n",
		"skills/not-a-skill/x.txt": "x\n",
		"mcp/servers.json":         `{"mcpServers":{"context7":{"type":"http","url":"https://mcp.context7.com/mcp"}}}`,
		"configs/targets.toml": `
[[links]]
tool = "claude"
src = "base/AGENTS.md"
dst = "~/.claude/AGENTS.md"

[[skills]]
tool = "claude"
dst = "~/.claude/skills"

[[mcp]]
tool = "codex"
format = "codex-toml"
path = "~/.codex/config.toml"

[[mcp]]
tool = "pi"
format = "mcp-json"
path = "~/.config/mcp/mcp.json"
`,
	}
	for name, content := range files {
		writeTestFile(t, filepath.Join(repo, name), content)
	}
	return repo
}

func writeTestFile(t *testing.T, path, content string) {
	t.Helper()
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatal(err)
	}
}

func readTestFile(t *testing.T, path string) string {
	t.Helper()
	data, err := os.ReadFile(path)
	if err != nil {
		t.Fatal(err)
	}
	return string(data)
}

func runSync(t *testing.T, repo, home string, dryRun bool) (*syncer, string) {
	t.Helper()
	cfg, err := loadConfig(filepath.Join(repo, "configs", "targets.toml"))
	if err != nil {
		t.Fatal(err)
	}
	var out bytes.Buffer
	s := &syncer{repo: repo, home: home, dryRun: dryRun, backupDir: filepath.Join(home, ".workbench-backup", "today"), out: &out}
	if err := s.syncAll(cfg); err != nil {
		t.Fatal(err)
	}
	return s, out.String()
}

func TestSyncIsIdempotent(t *testing.T) {
	repo, home := newRepo(t), t.TempDir()

	first, _ := runSync(t, repo, home, false)
	if first.changed == 0 {
		t.Fatal("第一次运行没有任何改动")
	}
	second, out := runSync(t, repo, home, false)
	if second.changed != 0 {
		t.Errorf("第二次运行有 %d 处改动，期望 0：\n%s", second.changed, out)
	}

	if got := readTestFile(t, filepath.Join(home, ".claude", "AGENTS.md")); got != "# 基底层\n" {
		t.Errorf("AGENTS.md = %q", got)
	}
	if got := readTestFile(t, filepath.Join(home, ".claude", "skills", "coding", "ref", "a.md")); got != "a\n" {
		t.Errorf("技能参考文件 = %q", got)
	}
	if _, err := os.Stat(filepath.Join(home, ".claude", "skills", "not-a-skill")); !os.IsNotExist(err) {
		t.Error("没有 SKILL.md 的目录不应被同步")
	}
}

func TestDryRunWritesNothing(t *testing.T) {
	repo, home := newRepo(t), t.TempDir()

	s, out := runSync(t, repo, home, true)
	if s.changed == 0 || !strings.Contains(out, "[dry-run]") {
		t.Errorf("dry-run 应打印将要做的改动，得到：\n%s", out)
	}
	entries, err := os.ReadDir(home)
	if err != nil {
		t.Fatal(err)
	}
	if len(entries) != 0 {
		t.Errorf("dry-run 不应写入任何文件，主目录里有 %d 项", len(entries))
	}
}

func TestExistingFileIsBackedUp(t *testing.T) {
	repo, home := newRepo(t), t.TempDir()
	dst := filepath.Join(home, ".claude", "AGENTS.md")
	writeTestFile(t, dst, "旧内容\n")

	runSync(t, repo, home, false)

	backup := filepath.Join(home, ".workbench-backup", "today", ".claude", "AGENTS.md")
	if got := readTestFile(t, backup); got != "旧内容\n" {
		t.Errorf("备份内容 = %q，期望旧内容", got)
	}
	if got := readTestFile(t, dst); got != "# 基底层\n" {
		t.Errorf("AGENTS.md = %q", got)
	}
}

func TestIdenticalCopyIsLeftAlone(t *testing.T) {
	repo, home := newRepo(t), t.TempDir()
	// 模拟 Windows 上之前因无法建链接而复制过来的副本。
	writeTestFile(t, filepath.Join(home, ".claude", "AGENTS.md"), "# 基底层\n")

	runSync(t, repo, home, false)

	info, err := os.Lstat(filepath.Join(home, ".claude", "AGENTS.md"))
	if err != nil {
		t.Fatal(err)
	}
	if info.Mode()&os.ModeSymlink != 0 {
		t.Error("内容相同的副本不应被替换")
	}
	if _, err := os.Stat(filepath.Join(home, ".workbench-backup")); !os.IsNotExist(err) {
		t.Error("内容相同时不应产生备份")
	}
}

func TestMergeCodexTOML(t *testing.T) {
	ss := servers{"context7": {Type: "http", URL: "https://mcp.context7.com/mcp"}}
	old := `model = "gpt-5"

[mcp_servers.context7]
command = "npx"
args = ["-y", "old"]

[mcp_servers.context7.env]
KEY = "v"

[mcp_servers.other]
command = "other"

[profiles.fast]
model = "mini"
`
	got := mergeCodexTOML(old, ss)

	for _, want := range []string{`model = "gpt-5"`, "[mcp_servers.other]", "[profiles.fast]", `url = "https://mcp.context7.com/mcp"`} {
		if !strings.Contains(got, want) {
			t.Errorf("结果缺少 %q：\n%s", want, got)
		}
	}
	for _, gone := range []string{`"old"`, "[mcp_servers.context7.env]", "npx"} {
		if strings.Contains(got, gone) {
			t.Errorf("结果不应包含 %q：\n%s", gone, got)
		}
	}
	if again := mergeCodexTOML(got, ss); again != got {
		t.Errorf("重复合并结果不同：\n%s\n---\n%s", got, again)
	}
}

func TestRenderCodexEnvRefs(t *testing.T) {
	ss := servers{
		"local": {Command: "npx", Args: []string{"-y", "pkg"}, Env: map[string]string{"TOKEN": "${TOKEN}", "MODE": "dev"}},
		"remote": {URL: "https://example.com/mcp", Headers: map[string]string{
			"Authorization": "Bearer ${API_KEY}",
			"X-Key":         "${X_KEY}",
			"X-Fixed":       "1",
		}},
	}
	got := renderCodex(ss)
	for _, want := range []string{
		`args = ["-y", "pkg"]`,
		`env = { MODE = "dev" }`,
		`env_vars = ["TOKEN"]`,
		`bearer_token_env_var = "API_KEY"`,
		`env_http_headers = { X-Key = "X_KEY" }`,
		`http_headers = { X-Fixed = "1" }`,
	} {
		if !strings.Contains(got, want) {
			t.Errorf("结果缺少 %q：\n%s", want, got)
		}
	}
}

func TestMergeMCPJSONKeepsOtherServers(t *testing.T) {
	ss := servers{"context7": {Type: "http", URL: "https://mcp.context7.com/mcp"}}
	old := []byte(`{"settings":{"x":1},"mcpServers":{"mine":{"command":"foo"},"context7":{"command":"stale"}}}`)

	out, err := mergeMCPJSON(old, ss)
	if err != nil {
		t.Fatal(err)
	}
	var doc struct {
		Settings   map[string]any            `json:"settings"`
		MCPServers map[string]map[string]any `json:"mcpServers"`
	}
	if err := json.Unmarshal(out, &doc); err != nil {
		t.Fatal(err)
	}
	if doc.Settings["x"] != float64(1) {
		t.Error("其他字段丢失")
	}
	if doc.MCPServers["mine"]["command"] != "foo" {
		t.Error("其他服务器丢失")
	}
	if doc.MCPServers["context7"]["url"] != "https://mcp.context7.com/mcp" || doc.MCPServers["context7"]["command"] != nil {
		t.Errorf("context7 未被替换：%v", doc.MCPServers["context7"])
	}
}

func TestLoadServersRejectsAmbiguous(t *testing.T) {
	path := filepath.Join(t.TempDir(), "servers.json")
	writeTestFile(t, path, `{"mcpServers":{"bad":{"command":"x","url":"https://x"}}}`)
	if _, err := loadServers(path); err == nil {
		t.Error("同时有 command 和 url 时应报错")
	}
}

func TestExpand(t *testing.T) {
	home := filepath.FromSlash("/home/u")
	tests := []struct{ in, want string }{
		{"~", home},
		{"~/.claude/skills", filepath.Join(home, ".claude", "skills")},
		{"/etc/x", filepath.FromSlash("/etc/x")},
	}
	for _, tt := range tests {
		if got := expand(tt.in, home); got != tt.want {
			t.Errorf("expand(%q) = %q, want %q", tt.in, got, tt.want)
		}
	}
}
