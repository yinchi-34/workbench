# prompt

个人提示词（Prompt）收藏库，用于整理、复用和迭代日常使用的 AI 提示词。

## 目录结构

```
.
├── prompts/            # 提示词正文，按用途分类
│   ├── coding/         # 编程相关：代码审查、重构、调试等
│   └── writing/        # 写作相关：润色、翻译、总结等
├── templates/          # 新建提示词时使用的模板
├── LICENSE
└── README.md
```

## 使用方式

1. 在 `prompts/` 下找到合适的分类（没有就新建一个子目录）。
2. 复制 `templates/prompt-template.md`，按模板填写。
3. 文件名使用小写英文加连字符，例如 `code-review.md`。

## 提示词文件格式

每个提示词是一个 Markdown 文件，包含：

- **用途**：这个提示词解决什么问题
- **适用模型**：测试过的模型（可选）
- **变量**：需要替换的占位符，统一写成 `{{变量名}}`
- **提示词**：正文
- **示例 / 备注**：效果示例、注意事项、修改记录

参考示例：[prompts/coding/code-review.md](prompts/coding/code-review.md)

## 许可证

见 [LICENSE](LICENSE)。
