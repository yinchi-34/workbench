# fullstack 模板

> 本文件只说明模板本身，复制到业务仓库时跳过它。

适用于前后端分离、按 [docs/workflow.md](../../docs/workflow.md) 多 agent 协作开发的仓库，第一个使用者是划词引用聊天应用（Go + Vue 3）。

| 文件 | 作用 | 继承方式 |
|------|------|----------|
| AGENTS.md | 仓库层：项目框架、规模估算、不做的事，`<!-- -->` 处由项目填写 | 复制一次 |
| CLAUDE.md | `@AGENTS.md` + Claude Code 的多 agent 编排规则 | 复制一次 |
| .claude/agents/ | 11 个子 agent：产品经理、前后端规划者 / 执行者 / 审查者、4 个后端专项审查 | 复制一次 |
| .claude/leads/ | 前后端负责人的会话说明（不是子 agent，见下） | 复制一次 |
| .claude/settings.json | 禁止助手推 main、禁止 --no-verify | 复制一次 |
| docs/specs/_template.md | 每个功能的 spec 模板 | 复制一次 |
| docs/api-index.md | 接口影响索引 | 复制一次 |
| docs/examples/ | 各角色输出的样板，prompt 里按路径引用 | 复制一次 |
| docs/notes/ | 问题记录 | 复制一次 |

lefthook.yml、CI、dependabot、PR 模板按语言从其他模板拿（Go 部分同 algorithm 模板）。

## 使用

1. 复制本目录内容到业务仓库，同名文件逐个对比合并。
2. 复制 workbench 的 `evals/checklists/common-issues.md` 到 `docs/checklist.md`。项目特有的坑加在后面，通用的坑回写 workbench。
3. 填 AGENTS.md：技术栈、目录、规模估算、不做的事。
4. 在 GitHub Projects 建看板，五列：待办、进行中、审查中、等我确认、已完成。

## 为什么负责人不是子 agent

Claude Code 的子 agent 不能再调用别的子 agent，跑完只能把结果交回主会话。负责人要调用规划者、执行者、审查者，所以必须是主会话：前后端各开一个会话、各用一个 git worktree，第一句话让它按 `.claude/leads/<frontend|backend>-lead.md` 工作。产品经理会话、两个负责人会话之间只通过 docs/specs/ 和 docs/api-index.md 沟通。

这套分工还没实际跑过，第一次用时按实际情况调整，改动记进 workbench 的 CHANGELOG.md。
