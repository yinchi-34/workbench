以下为格式示例，非真实执行或批准记录。填写实际信息后使用。

状态：待人工决定
任务：B3，发送消息接口支持引用（示例）
依据：待填写实际 spec / 契约版本与提交 SHA
产出：下方角色附件
验证：待按 AC 补充实际结果与证据，示例结果不作为证据
问题：待核实
决策请求：待填实际问题、选项、推荐与影响
下一步：项目管理核对后转交人工或下一角色

## 角色附件

### 任务 B3：发送消息接口支持引用
- 目标：POST /api/conversations/:id/messages 可接收 quotes 数组并写入数据库
- 涉及文件：internal/handler/message.go、internal/store/quote.go
- 依赖：B1（quotes 表已建立）
- 验收测试：internal/handler/message_test.go
  - 携带 1 段合法引用 → 201，数据库中有 1 条 quote
  - source_message_id 属于其他会话 → 400
  - text 超过 2000 字 → 400
  - quotes 超过 3 段 → 400
- 专项审查：数据库、接口与安全
- 注意事项：消息与引用须在同一事务中写入；校验引用归属时避免逐条查询数据库
