# 角色 prompt（通用版）

本目录的 prompt 不绑定具体工具，适用于任何支持按角色调用模型的环境：将对应文件的内容作为该角色的系统提示词，`<>` 处按项目填写。可在 Claude Code 中直接使用的版本见 [templates/fullstack/](../../templates/fullstack/TEMPLATE.md)。

各 prompt 按统一顺序编写：背景、步骤、输出格式、规则（附理由）、需提交用户确认的情形。输出格式参照 templates/fullstack/docs/examples/ 中的示例。

| 文件 | 角色 | 层级 | 建议模型 |
|------|------|------|----------|
| product-manager.md | 产品经理（用户与 agent 共同担任） | 一 | 强模型 |
| lead.md | 前端 / 后端负责人 | 二 | 强模型 |
| planner.md | 前端 / 后端规划者 | 三 | 强模型 |
| executor.md | 前端 / 后端执行者 | 四 | 执行模型 |
| reviewer.md | 前端 / 后端审查者 | 四 | 强模型，且不得为编写代码的同一 agent |
| specialist-reviewer.md | 后端专项审查（数据库 / 缓存 / 并发与流式 / 接口与安全） | 四 | 强模型 |
