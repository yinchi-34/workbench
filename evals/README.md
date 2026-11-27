# 评测

| 目录 | 内容 |
|------|------|
| checklists/ | 测试点清单（algorithm.md）和常见问题清单（common-issues.md，验收和专项审查用） |
| prompts/results/ | 第 3 层：工作流质量记录 |

## 基线记录格式

每完成一个任务追加一行到 `prompts/results/baseline.csv`：

| 列 | 含义 |
|----|------|
| date | 日期，YYYY-MM-DD |
| repo | 业务仓库 |
| task | 任务，例如题目 slug |
| implementer / reviewer | 实现方和审查方，例如 claude-code、codex-github |
| skills | 用到的技能及版本，分号分隔，例如 `solve-problem@v1;write-tests@v1;code-review@v1` |
| first_ci_pass | 第一次推送 CI 是否通过，yes/no |
| rework_count | 审查后返工次数 |
| minutes | 从开始到合并的总时长 |
| tokens | 用 `npx ccusage session` 查到的该会话 token 数 |
| notes | 卡在哪里、哪条规则没生效 |

这一行是以后对比技能改版、对比模型的起点。
