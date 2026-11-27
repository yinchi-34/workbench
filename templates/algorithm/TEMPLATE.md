# algorithm 模板

> 本文件只说明模板本身，复制到业务仓库时跳过它。

适用于刷题、算法练习类的 Go 仓库，第一个使用者是 leetcode-go。

| 文件 | 作用 | 继承方式 |
|------|------|----------|
| AGENTS.md | 仓库层骨架，`<!-- -->` 处由项目填写 | 复制一次 |
| CLAUDE.md | 一行 `@AGENTS.md` | 复制一次 |
| lefthook.yml | pre-commit：gofmt、go vet、gitleaks；pre-push：go test | 复制一次 |
| .golangci.yml | lint 规则 | 复制一次 |
| .github/workflows/ci.yml | 调用 workbench 的 go-ci.yml，固定版本号 | 引用 |
| .github/dependabot.yml | Go 模块和 Actions 版本更新 | 复制一次 |
| .github/pull_request_template.md | PR 说明模板 | 复制一次 |
| .claude/settings.json | 禁止助手推 main、禁止 --no-verify | 复制一次 |
| docs/specs/、docs/notes/ | 功能规格、踩坑记录 | 复制一次 |

## 使用

方式一：把本目录内容推到独立的模板仓库 tpl-algorithm-go（勾选 Template repository），之后用 `gh repo create <名字> --private --template yinchi-34/tpl-algorithm-go` 新建。

方式二：直接复制本目录内容到已有仓库，同名文件逐个对比合并。

新仓库克隆后运行一次 `lefthook install`。
