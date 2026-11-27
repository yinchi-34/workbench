完成

## 任务 B3 完成报告
- 修改的文件：message.go、quote.go
- 代码与功能点的对应关系：
  - message.go 第 42-58 行：校验 quotes 的数量与长度
  - quote.go 第 15-30 行：以一次查询校验全部引用的会话归属
  - message.go 第 60-75 行：在同一事务中写入消息与引用
- 测试结果：ok internal/handler 0.31s（4/4 通过）
- 自查结果：事务 ✓；归属校验为批量查询，未逐条查询 ✓
- 尚不确定之处：quotes 为空数组与未传 quotes 两种情况，目前均按"无引用"处理
