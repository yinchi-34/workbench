package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"os"
	"os/exec"
	"reflect"
	"regexp"
	"sort"
	"strings"
)

// server 是 mcp/servers.json 里 mcpServers 的一项，采用标准格式。
// 密钥只写成 ${VAR} 形式的环境变量引用。
type server struct {
	Type    string            `json:"type,omitempty"`
	Command string            `json:"command,omitempty"`
	Args    []string          `json:"args,omitempty"`
	Env     map[string]string `json:"env,omitempty"`
	URL     string            `json:"url,omitempty"`
	Headers map[string]string `json:"headers,omitempty"`
}

type servers map[string]server

func loadServers(path string) (servers, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	var doc struct {
		MCPServers servers `json:"mcpServers"`
	}
	dec := json.NewDecoder(bytes.NewReader(data))
	dec.DisallowUnknownFields()
	if err := dec.Decode(&doc); err != nil {
		return nil, fmt.Errorf("解析 %s：%w", path, err)
	}
	for name, srv := range doc.MCPServers {
		if (srv.Command == "") == (srv.URL == "") {
			return nil, fmt.Errorf("%s：%s 必须且只能有 command 或 url 之一", path, name)
		}
	}
	return doc.MCPServers, nil
}

func (ss servers) names() []string {
	names := make([]string, 0, len(ss))
	for name := range ss {
		names = append(names, name)
	}
	sort.Strings(names)
	return names
}

func (s *syncer) syncMCP(t mcpTarget, ss servers) error {
	switch t.Format {
	case "codex-toml":
		return s.syncCodex(expand(t.Path, s.home), ss)
	case "mcp-json":
		return s.syncMCPJSON(expand(t.Path, s.home), ss)
	case "claude-cli":
		return s.syncClaude(expand(t.State, s.home), ss)
	default:
		return fmt.Errorf("不支持的格式 %q", t.Format)
	}
}

// ---- Codex：~/.codex/config.toml ----

func (s *syncer) syncCodex(path string, ss servers) error {
	old, err := os.ReadFile(path)
	if err != nil && !os.IsNotExist(err) {
		return err
	}
	return s.writeFile(path, []byte(mergeCodexTOML(string(old), ss)))
}

// mergeCodexTOML 删掉 config 里由 workbench 管理的 [mcp_servers.<名字>] 表
// （含子表），再把新生成的表追加到末尾；其他内容原样保留。
func mergeCodexTOML(config string, ss servers) string {
	var kept []string
	skipping := false
	for _, line := range strings.Split(config, "\n") {
		if name, ok := tableHeader(line); ok {
			skipping = isManagedTable(name, ss)
		}
		if !skipping {
			kept = append(kept, line)
		}
	}
	out := strings.TrimRight(strings.Join(kept, "\n"), "\n")
	if out != "" {
		out += "\n\n"
	}
	return out + renderCodex(ss)
}

var headerRe = regexp.MustCompile(`^\s*\[\[?\s*([^\]]+?)\s*\]\]?\s*(#.*)?$`)

func tableHeader(line string) (string, bool) {
	m := headerRe.FindStringSubmatch(line)
	if m == nil {
		return "", false
	}
	return m[1], true
}

func isManagedTable(table string, ss servers) bool {
	rest, ok := strings.CutPrefix(table, "mcp_servers.")
	if !ok {
		return false
	}
	for name := range ss {
		for _, key := range []string{name, `"` + name + `"`} {
			if rest == key || strings.HasPrefix(rest, key+".") {
				return true
			}
		}
	}
	return false
}

var envRefRe = regexp.MustCompile(`^\$\{([A-Za-z_][A-Za-z0-9_]*)\}$`)
var bearerRefRe = regexp.MustCompile(`^Bearer \$\{([A-Za-z_][A-Za-z0-9_]*)\}$`)

func renderCodex(ss servers) string {
	var b strings.Builder
	for i, name := range ss.names() {
		srv := ss[name]
		if i > 0 {
			b.WriteString("\n")
		}
		fmt.Fprintf(&b, "[mcp_servers.%s]\n", tomlKey(name))
		if srv.Command != "" {
			fmt.Fprintf(&b, "command = %s\n", tomlString(srv.Command))
			if len(srv.Args) > 0 {
				fmt.Fprintf(&b, "args = %s\n", tomlArray(srv.Args))
			}
			// ${VAR} 让 Codex 从环境变量转发，其他值原样写入。
			literal := map[string]string{}
			var forward []string
			for k, v := range srv.Env {
				if m := envRefRe.FindStringSubmatch(v); m != nil && m[1] == k {
					forward = append(forward, k)
				} else {
					literal[k] = v
				}
			}
			if len(literal) > 0 {
				fmt.Fprintf(&b, "env = %s\n", tomlInlineTable(literal))
			}
			if len(forward) > 0 {
				sort.Strings(forward)
				fmt.Fprintf(&b, "env_vars = %s\n", tomlArray(forward))
			}
			continue
		}

		fmt.Fprintf(&b, "url = %s\n", tomlString(srv.URL))
		literal := map[string]string{}
		fromEnv := map[string]string{}
		for k, v := range srv.Headers {
			if m := bearerRefRe.FindStringSubmatch(v); m != nil && strings.EqualFold(k, "Authorization") {
				fmt.Fprintf(&b, "bearer_token_env_var = %s\n", tomlString(m[1]))
			} else if m := envRefRe.FindStringSubmatch(v); m != nil {
				fromEnv[k] = m[1]
			} else {
				literal[k] = v
			}
		}
		if len(literal) > 0 {
			fmt.Fprintf(&b, "http_headers = %s\n", tomlInlineTable(literal))
		}
		if len(fromEnv) > 0 {
			fmt.Fprintf(&b, "env_http_headers = %s\n", tomlInlineTable(fromEnv))
		}
	}
	return b.String()
}

var bareKeyRe = regexp.MustCompile(`^[A-Za-z0-9_-]+$`)

func tomlKey(k string) string {
	if bareKeyRe.MatchString(k) {
		return k
	}
	return tomlString(k)
}

func tomlString(s string) string {
	var b strings.Builder
	b.WriteByte('"')
	for _, r := range s {
		switch r {
		case '"':
			b.WriteString(`\"`)
		case '\\':
			b.WriteString(`\\`)
		case '\n':
			b.WriteString(`\n`)
		case '\t':
			b.WriteString(`\t`)
		case '\r':
			b.WriteString(`\r`)
		default:
			if r < 0x20 || r == 0x7f {
				fmt.Fprintf(&b, `\u%04X`, r)
			} else {
				b.WriteRune(r)
			}
		}
	}
	b.WriteByte('"')
	return b.String()
}

func tomlArray(items []string) string {
	quoted := make([]string, len(items))
	for i, s := range items {
		quoted[i] = tomlString(s)
	}
	return "[" + strings.Join(quoted, ", ") + "]"
}

func tomlInlineTable(m map[string]string) string {
	keys := make([]string, 0, len(m))
	for k := range m {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	pairs := make([]string, len(keys))
	for i, k := range keys {
		pairs[i] = tomlKey(k) + " = " + tomlString(m[k])
	}
	return "{ " + strings.Join(pairs, ", ") + " }"
}

// ---- pi（pi-mcp-adapter）：标准 mcpServers JSON ----

func (s *syncer) syncMCPJSON(path string, ss servers) error {
	old, err := os.ReadFile(path)
	if err != nil && !os.IsNotExist(err) {
		return err
	}
	merged, err := mergeMCPJSON(old, ss)
	if err != nil {
		return fmt.Errorf("%s：%w", path, err)
	}
	return s.writeFile(path, merged)
}

// mergeMCPJSON 只替换同名条目，文件里的其他字段和其他服务器保留。
func mergeMCPJSON(old []byte, ss servers) ([]byte, error) {
	doc := map[string]any{}
	if len(bytes.TrimSpace(old)) > 0 {
		if err := json.Unmarshal(old, &doc); err != nil {
			return nil, err
		}
	}
	existing, _ := doc["mcpServers"].(map[string]any)
	if existing == nil {
		existing = map[string]any{}
	}
	for name, srv := range ss {
		v, err := toGeneric(srv)
		if err != nil {
			return nil, err
		}
		existing[name] = v
	}
	doc["mcpServers"] = existing
	out, err := json.MarshalIndent(doc, "", "  ")
	if err != nil {
		return nil, err
	}
	return append(out, '\n'), nil
}

func toGeneric(v any) (any, error) {
	data, err := json.Marshal(v)
	if err != nil {
		return nil, err
	}
	var g any
	err = json.Unmarshal(data, &g)
	return g, err
}

// ---- Claude Code：claude mcp add-json --scope user ----

func (s *syncer) syncClaude(statePath string, ss servers) error {
	current := map[string]any{}
	if data, err := os.ReadFile(statePath); err == nil {
		var state struct {
			MCPServers map[string]any `json:"mcpServers"`
		}
		if err := json.Unmarshal(data, &state); err != nil {
			return fmt.Errorf("解析 %s：%w", statePath, err)
		}
		current = state.MCPServers
	} else if !os.IsNotExist(err) {
		return err
	}

	for _, name := range ss.names() {
		want, err := toGeneric(ss[name])
		if err != nil {
			return err
		}
		have, exists := current[name]
		if exists && reflect.DeepEqual(have, want) {
			continue
		}

		s.changed++
		payload, _ := json.Marshal(ss[name])
		s.logf("claude mcp add-json --scope user %s %s", name, payload)
		if s.dryRun {
			continue
		}
		if _, err := exec.LookPath("claude"); err != nil {
			s.logf("警告：找不到 claude 命令，跳过 %s", name)
			continue
		}
		if exists {
			if out, err := s.claude("mcp", "remove", "--scope", "user", name); err != nil {
				return fmt.Errorf("claude mcp remove %s：%w\n%s", name, err, out)
			}
		}
		if out, err := s.claude("mcp", "add-json", "--scope", "user", name, string(payload)); err != nil {
			return fmt.Errorf("claude mcp add-json %s：%w\n%s", name, err, out)
		}
	}
	return nil
}

// claude 运行 claude 命令，主目录与 -home 一致，保证写入的就是读取状态的那份配置。
func (s *syncer) claude(args ...string) ([]byte, error) {
	cmd := exec.Command("claude", args...)
	cmd.Env = append(os.Environ(), "HOME="+s.home, "USERPROFILE="+s.home)
	return cmd.CombinedOutput()
}
