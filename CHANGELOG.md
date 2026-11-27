# 更新记录

## 未发布

- fullstack 模板新增测试保护钩子 protect_tests.py：禁止 agent 修改已有测试文件，允许新建。
- merge.py：PR 修改、删除或重命名已有测试文件时拒绝合并，指定 --allow-test-changes 方可合并。
- 新增 AI 协作开发工作流：docs/workflow.md、常见问题清单、tech-research 技能（v1）、通用版角色 prompt（v2，流程为后端补充 API 与数据模型、前端反馈、双方交互一轮）、fullstack 模板（Claude Code 子 agent、负责人会话说明、spec 模板、接口影响索引、输出示例）。
- 初始化仓库骨架：基底层、code-review 和 write-tests 技能（v1）、algorithm 模板、可复用 Go CI、MCP 配置（Context7）、Python 同步脚本、评测基线格式。
- 新增 bootstrap.py（检查工具、装 ccusage、配状态栏）和 merge.py（检查全部通过才合并）。
