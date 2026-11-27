# AI 协作开发工作流：细则

流程概述见 [README](../README.md#开发流程)。本文记录第二至四步的细则；第一步已拆分为 requirements-design 技能，此处只列要点。文中"开发者"指使用本流程的人，负责审核与最终决策。

## 第一步：需求设计

由 [requirements-design](../skills/requirements-design/SKILL.md) 技能执行，产出 docs/specs/<功能名>.md，并确定协作档位（轻量或完整）。项目级规模估算、spec 模板、按功能类型区分的参考内容、两档协作方式的角色与分层，均见该技能的 references 目录。

## 第二步：任务拆分与多 agent 协作

1. 每个阶段按前端、后端拆分为小任务，每个任务明确实现方式、涉及文件和验收测试。
2. **按模型能力分工**：能力较强的模型负责分析、拆分任务和审查；执行模型负责实现。
3. **测试先行**：规划者将验收测试写成测试文件，执行者的职责是使测试通过。
4. **交叉审查**：测试本身同样需要审查，编写代码的 agent 不得审查自己的产出。

角色设置取决于第一步确定的协作档位：轻量档位见 [team-lite.md](../skills/requirements-design/references/team-lite.md)，完整档位见 [team-full.md](../skills/requirements-design/references/team-full.md)。

### 看板

暂时使用 GitHub Projects。

- 列：待办、进行中、审查中、待确认、已完成
- 每张卡片对应一个任务，并链接到对应的 spec 与任务说明
- 卡片状态随流程更新；收到首行为"需要确认"的报告时，将卡片移至"待确认"

### 接口变更规则

- 首先判断变更原因：仅因界面调整而变更的，只修改前端；涉及流程逻辑，或需新增字段、ID 的，前后端同步修改。
- 接口契约（spec 中的 API 设计与 docs/api-index.md）是唯一依据，前后端均以其为准，不得各自修改。
- 变更由产品经理提出，经开发者批准后同时下发前后端。后端先更新契约与 mock，前端依据契约并行开发。

### 接口影响索引

参照 RBAC 的分层判断思路：接口按层级管理，修改任一接口前，AI 须先查阅索引，明确受影响的范围后再进行修改。模板见 [templates/fullstack/docs/api-index.md](../templates/fullstack/docs/api-index.md)。

- **层级**分为三类：对外接口、内部接口、基础能力。层级越低，依赖方越多，修改风险越高。
- **修改规则**：修改接口时，须逐项检查"谁依赖它"一栏，并写入影响说明。涉及对外接口的，按接口契约变更处理，须经开发者批准。

### 人工审核节点（HITL）

两种档位均在以下节点暂停流程，经开发者确认后方可继续：

1. 需求确认：spec 定稿
2. 接口契约变更
3. 对测试文件的任何修改
4. 同一问题连续两次未能解决
5. 最终验收

## 第三步：问题处理

1. **问题记录**：每遇到一个问题即时记录 AI 的输出、发现问题的方式及修复过程，存放于业务仓库的 docs/notes/；复盘时由 retro 技能在 workbench 的问题索引中登记。
2. **测试持续失败**：测试文件须经开发者同意方可修改，以防 AI 放宽断言或跳过测试；同一问题连续两次未能解决时，暂停并转入人工审核。该约束同时由工具执行：钩子禁止 agent 修改已有测试文件，merge.py 在合并时再次检查（见 fullstack 模板的"测试保护"一节）。
3. **代码可追溯**：执行者须在报告中注明代码行与功能点的对应关系，开发者据此进行整体抽查。
4. **经验沉淀**：通用问题补充至 [常见问题清单](../evals/checklists/common-issues/README.md)，并同步更新相关角色的 prompt。

## 第四步：收尾验收与复盘

验收分为三步：

1. **测试检查**：流程完整、覆盖全部需求、全部通过。
2. **实际操作**：由开发者亲自完整使用一遍功能，包括异常路径。
3. **清单检查**：按常见问题清单逐项核对，其中资源开销层须与 spec 中的估算对照。

验收完成（或功能中止）后，使用 [retro](../skills/retro/SKILL.md) 技能复盘，将结果汇总到 workbench 的 [跨项目记录](../evals/records/README.md)：

| 记录 | 内容 |
|------|------|
| 进度汇总 | 每个功能的当前阶段、协作档位、工具、返工次数 |
| 问题索引 | 每个问题的层次、范围与清单回写情况，详细记录链接回业务仓库 |
| 基线数据 | 每个任务的首次 CI 通过情况、返工次数、耗时与 token 数 |

进度汇总在阶段变化时也可随时更新，不必等到复盘。

## Prompt 版本管理

每个技能均标注版本号（标题中的 v1、v2 等），修改原因记录于 CHANGELOG.md。发现新问题或清单更新时，同步升级相关的角色技能。角色正文只在 role-* 技能中维护一份，Claude Code 子 agent 文件仅保留配置，以保证不同工具读取的内容一致。

## 相关文件

| 内容 | 位置 |
|------|------|
| 需求设计技能及参考文件 | [skills/requirements-design/](../skills/requirements-design/SKILL.md) |
| 新功能调研技能 | [skills/tech-research/](../skills/tech-research/SKILL.md) |
| 复盘技能与跨项目记录 | [skills/retro/](../skills/retro/SKILL.md)、[evals/records/](../evals/records/README.md) |
| 常见问题清单（七层） | [evals/checklists/common-issues/](../evals/checklists/common-issues/README.md) |
| 协作角色技能（Claude Code 与 Codex 共用） | [skills/role-*/](../skills/) |
| Claude Code 子 agent 配置、接口影响索引、测试保护钩子 | [templates/fullstack/](../templates/fullstack/TEMPLATE.md) |
