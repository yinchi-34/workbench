# workbench

个人 AI 编程工作流仓库：让 Claude Code、Codex、pi 在不同业务仓库里遵守同一套规则、技能和检查。

原则：跨仓库复用的放这里，只属于某个项目的留在那个项目里；能被工具检查的交给工具，不写进提示词。

## 目录

```
workbench/
├── base/                     # 基底层：所有仓库、所有助手共用
│   ├── AGENTS.md             # 60 行以内的工程原则
│   └── CLAUDE.md             # 一行 @AGENTS.md
├── skills/                   # 通用技能
│   └── coding/               # 写代码、审代码、写测试
│       ├── SKILL.md
│       └── references/       # review.md、tests.md，用到时才加载
├── templates/
│   └── algorithm/            # 刷题类 Go 仓库模板（说明见 TEMPLATE.md）
├── .github/workflows/
│   ├── go-ci.yml             # 可复用 CI：gofmt、vet、golangci-lint、test；main 失败开 issue
│   └── ci.yml                # 本仓库自身的 CI
├── mcp/servers.json          # 通用 MCP，统一用标准 mcpServers 格式
├── configs/targets.toml      # 各工具读取规则、技能、MCP 的位置
├── scripts/sync/             # 同步脚本（Go）
└── evals/                    # 测试点清单、基线记录
```

## 同步到各工具

需要 Go 1.24 以上。在本仓库根目录：

```sh
go run ./scripts/sync -dry-run   # 先看会改什么
go run ./scripts/sync            # 执行
```

Windows、WSL、Linux 各自是独立的主目录，每个环境各跑一次。

同步内容和目标位置见 [configs/targets.toml](configs/targets.toml)：

| 内容 | Claude Code | Codex | pi |
|------|-------------|-------|----|
| 基底层 | ~/.claude/AGENTS.md + CLAUDE.md | ~/.codex/AGENTS.md | ~/.pi/agent/AGENTS.md |
| 技能 | ~/.claude/skills/ | ~/.agents/skills/ | ~/.agents/skills/ |
| MCP | `claude mcp add-json --scope user` | ~/.codex/config.toml 的 mcp_servers | ~/.config/mcp/mcp.json（需装 pi-mcp-adapter） |

脚本行为：

- 能建符号链接就建链接；Windows 没开开发者模式时自动改为复制（改了仓库内容要重新跑）。
- 覆盖已有文件前备份到 `~/.workbench-backup/<日期>/`。
- Codex 的 config.toml 只替换同名的 `[mcp_servers.<名字>]` 表，其他设置保留；pi 的 mcp.json 只替换同名条目。
- 重复运行结果不变，第二次会提示“全部已是最新”。

## MCP

只在 [mcp/servers.json](mcp/servers.json) 里改，其他格式由同步脚本生成。密钥只写成 `${VAR}` 环境变量引用，例如给 Context7 加 API key：

```json
"headers": { "CONTEXT7_API_KEY": "${CONTEXT7_API_KEY}" }
```

转换到 Codex 时，`${VAR}` 形式的请求头变成 `env_http_headers`，`Authorization: Bearer ${VAR}` 变成 `bearer_token_env_var`。

## 新建业务仓库

见 [templates/algorithm/TEMPLATE.md](templates/algorithm/TEMPLATE.md)。业务仓库的 CI 只写几行调用本仓库的 go-ci.yml 并固定版本号；本仓库是私有的话，需要在 Settings → Actions → General → Access 里允许自己名下的其他仓库调用。

## 开发

```sh
gofmt -l . && go vet ./... && golangci-lint run && go test ./...
```
