# fullstack 模板

> 本文件仅说明模板本身，复制到业务仓库时跳过。

适用于前后端分离、按 [docs/workflow.md](../../docs/workflow.md) 进行多 agent 协作开发的仓库。首个使用场景为划词引用聊天应用（Go + Vue 3）。

| 文件 | 作用 | 继承方式 |
|------|------|----------|
| AGENTS.md | 仓库层规则：项目框架、规模估算、不做的事，`<!-- -->` 处由项目填写 | 复制一次 |
| CLAUDE.md | `@AGENTS.md` 及 Claude Code 的多 agent 编排规则 | 复制一次 |
| .claude/agents/ | 11 个子 agent：产品经理，前后端规划者、执行者、审查者，4 个后端专项审查者 | 复制一次 |
| .claude/leads/ | 前后端负责人的会话工作说明（不是子 agent，原因见下文） | 复制一次 |
| .claude/settings.json | 禁止助手推送 main、禁止 --no-verify，并配置测试保护钩子 | 复制一次 |
| .claude/hooks/protect_tests.py | PreToolUse 钩子：禁止 agent 修改已有测试文件，允许新建 | 复制一次 |
| docs/specs/_template.md | 功能 spec 模板 | 复制一次 |
| docs/api-index.md | 接口影响索引 | 复制一次 |
| docs/examples/ | 各角色输出格式的示例，角色 prompt 按路径引用 | 复制一次 |
| docs/notes/ | 问题记录 | 复制一次 |

lefthook.yml、CI、dependabot、PR 模板按语言从其他模板选取（Go 部分与 algorithm 模板相同）。

## 使用方法

1. 将本目录内容复制到业务仓库，同名文件逐一比对后合并。
2. 将 workbench 的 `evals/checklists/common-issues.md` 复制为 `docs/checklist.md`。项目特有的问题追加在后面，通用问题回写至 workbench。
3. 填写 AGENTS.md：技术栈、目录结构、规模估算、不做的事。
4. 在 GitHub Projects 中建立看板，设五列：待办、进行中、审查中、待确认、已完成。

## 测试保护

采用两层机制，后一层作为前一层的补充：

1. **钩子**（protect_tests.py）：agent 通过 Edit / Write / MultiEdit 修改已有测试文件时，操作被拒绝；新建测试文件不受限制，以便规划者编写测试。通过 Bash 命令（如 sed -i）进行的修改无法拦截。
2. **合并检查**（workbench 的 merge.py）：PR 修改、删除或重命名已有测试文件时拒绝合并；开发者审阅相关测试后，加 `--allow-test-changes` 参数方可合并。

已有测试如需修改，由开发者本人操作。Windows 原生环境若无 `python3` 命令，须将 settings.json 中的 `python3` 改为 `python`。

## 负责人不作为子 agent 的原因

Claude Code 的子 agent 不能调用其他子 agent，运行结束后只能将结果交回主会话。负责人需要调用规划者、执行者和审查者，因此必须作为主会话运行：前后端各开一个会话，各使用一个 git worktree，首条消息要求其按 `.claude/leads/<frontend|backend>-lead.md` 工作。产品经理会话与两个负责人会话之间仅通过 docs/specs/ 与 docs/api-index.md 沟通。

该分工尚未经过实际项目验证，首次使用时根据实际情况调整，并将改动记录于 workbench 的 CHANGELOG.md。
