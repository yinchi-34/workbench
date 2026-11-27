@AGENTS.md

## 多 agent 工作流（Claude Code）

子 agent 跑完只会把结果交回主会话，中途不能停下来等人，也不能调用别的子 agent。所以人工确认和转发都由主会话做；子 agent 遇到要人决定的事，提前结束，在报告第一行写"需要确认"。

### 会话分工

- **产品经理会话**：每个功能先开这个主会话，调用 product-manager 出 spec 初稿。
- **前端负责人会话、后端负责人会话**：各开一个，各用一个 git worktree。第一句话让它按 `.claude/leads/<frontend|backend>-lead.md` 工作。三个会话只通过 docs/specs/ 和 docs/api-index.md 沟通。

### 调用顺序

1. 新需求 → product-manager 写 spec 的系统设计 → 给人审核，确认后继续
2. 后端负责人补 API 设计和数据模型、更新 api-index → 前端负责人写"前端反馈" → 两边交互一轮 → 给人审核
3. 各负责人调用本领域的 planner 拆任务、写验收测试 → 任务列表给人过目
4. 每个任务 → 对应的 executor → 对应的 reviewer
5. 任务标了专项 → 再调用对应的专项 reviewer（db / cache / concurrency / security）
6. 审查结论是"打回" → 把审查报告交给 executor 重做，最多两轮，还不过就找人

### 必须停下来问人的情况

- 任何子 agent 的报告第一行是"需要确认"
- spec 定稿、接口契约变更、任何对测试文件的修改
- 同一个任务打回两次
- 最终验收

### 转发规则

子 agent 之间不能直接沟通。前后端关于接口的分歧，交给产品经理会话里的 product-manager 判断，人决定后再写回 spec。
