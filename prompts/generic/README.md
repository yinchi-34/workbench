# 角色 prompt（通用版）

不绑定任何工具，任何能分角色调用模型的环境都能用：把对应文件的内容作为该角色的系统提示词，`<>` 处按项目填写。Claude Code 里直接用的版本见 [templates/fullstack/](../../templates/fullstack/TEMPLATE.md)。

每个 prompt 按固定顺序写：背景、步骤、输出格式、规则（附理由）、什么时候停下来问我。输出格式参照 templates/fullstack/docs/examples/ 里的样板。

| 文件 | 角色 | 层级 | 建议模型 |
|------|------|------|----------|
| product-manager.md | 产品经理（我 + agent） | 一 | 强模型 |
| lead.md | 前端 / 后端负责人 | 二 | 强模型 |
| planner.md | 前端 / 后端规划者 | 三 | 强模型 |
| executor.md | 前端 / 后端执行者 | 四 | 执行模型 |
| reviewer.md | 前端 / 后端审查者 | 四 | 强模型，且不是写代码的那个 |
| specialist-reviewer.md | 后端专项审查（数据库 / 缓存 / 并发与流式 / 接口与安全） | 四 | 强模型 |
