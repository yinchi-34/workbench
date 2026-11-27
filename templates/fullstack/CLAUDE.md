@AGENTS.md

## 多 agent 工作流（Claude Code）

子 agent 运行结束后只能将结果交回主会话，运行过程中无法暂停等待人工确认，也不能调用其他子 agent。因此人工确认与信息转发均由主会话负责；子 agent 遇到需要人工决定的事项时提前结束，并在报告首行写明"需要确认"。

### 会话分工

- **产品经理会话**：每个功能首先开启该主会话，调用 product-manager 起草 spec。
- **前端负责人会话、后端负责人会话**：各开一个，各使用一个 git worktree，首条消息以参数形式调用 role-lead 技能，例如 `/role-lead 后端 带引用发送消息`。三个会话之间仅通过 docs/specs/ 与 docs/api-index.md 沟通。

### 调用顺序

1. 新需求 → product-manager 按 requirements-design 技能编写 spec 的系统设计，并确定协作档位 → 提交人工审核，确认后继续
   - 档位为轻量时：不启用负责人会话，在当前会话中直接执行第 3 至 6 步
2. 后端负责人补充 API 设计与数据模型并更新 api-index → 前端负责人填写"前端反馈" → 双方交互一轮 → 提交人工审核
3. 各负责人调用本领域的 planner 拆分任务、编写验收测试 → 任务列表提交人工审阅
4. 每个任务 → 对应的 executor → 对应的 reviewer
5. 任务标注了专项审查 → 调用对应的专项 reviewer（db / cache / concurrency / security）
6. 审查结论为"打回" → 将审查报告交给 executor 返工，最多两轮，仍未通过则提交人工处理

### 必须提交人工确认的情形

- 任一子 agent 的报告首行为"需要确认"
- spec 定稿、接口契约变更、对测试文件的任何修改
- 同一任务被打回两次
- 最终验收

### 转发规则

子 agent 之间不能直接通信。前后端对接口的分歧，交由产品经理会话中的 product-manager 分析，人工决定后写回 spec。
