完成

## 任务 B3 完成报告
- 改动的文件：message.go、quote.go
- 代码和功能的对应：
  - message.go 42-58 行：校验 quotes 数量和长度
  - quote.go 15-30 行：一次查询校验所有引用的会话归属
  - message.go 60-75 行：在同一个事务里写入消息和引用
- 测试结果：ok internal/handler 0.31s（4/4 通过）
- 自查结果：事务 ✓；归属校验是批量查询，没有逐条查 ✓
- 不确定的地方：quotes 为空数组和不传 quotes 时，目前都按"没有引用"处理
