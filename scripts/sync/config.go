package main

import (
	"fmt"
	"path/filepath"
	"strings"

	"github.com/BurntSushi/toml"
)

type config struct {
	Links  []linkTarget  `toml:"links"`
	Skills []skillTarget `toml:"skills"`
	MCP    []mcpTarget   `toml:"mcp"`
}

type linkTarget struct {
	Tool string `toml:"tool"`
	Src  string `toml:"src"`
	Dst  string `toml:"dst"`
}

type skillTarget struct {
	Tool string `toml:"tool"`
	Dst  string `toml:"dst"`
}

type mcpTarget struct {
	Tool   string `toml:"tool"`
	Format string `toml:"format"`
	Path   string `toml:"path"`
	State  string `toml:"state"`
}

func loadConfig(path string) (*config, error) {
	var cfg config
	md, err := toml.DecodeFile(path, &cfg)
	if err != nil {
		return nil, fmt.Errorf("读取 %s：%w", path, err)
	}
	if undecoded := md.Undecoded(); len(undecoded) > 0 {
		return nil, fmt.Errorf("%s 有无法识别的字段：%v", path, undecoded)
	}
	return &cfg, nil
}

// expand 把 ~ 换成主目录，并统一成当前系统的路径分隔符。
func expand(path, home string) string {
	if path == "~" {
		return home
	}
	if strings.HasPrefix(path, "~/") {
		return filepath.Join(home, filepath.FromSlash(path[2:]))
	}
	return filepath.FromSlash(path)
}
