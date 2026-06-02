# YouTube 字幕 Markdown 排版优化指南

> 本文件仅在用户说出"优化排版""突出重点""关键字加颜色"等触发词时读取。

## 核心原则

1. 先读取用户指定或刚生成的 Markdown 文件。
2. 保留原文含义和重要结论；如果用户明确说"保留原文"，把原始逐字稿放进折叠 callout 或 `<details>`，不要删除。
3. 用 `##`、`###`、编号章节和 `---` 分隔线建立清晰层级。
4. 把密集对比改成表格。
5. 需要用户后续执行的地方，整理成 `- [ ]` 自查清单。
6. 不要过度装饰。
7. 完成后检查 Markdown：表格、callout、HTML 标签、代码块必须完整。

## 排版样式

对关键词适度使用 Obsidian/Markdown 样式：

- `**加粗**`：一级重点。
- `*斜体*`：二级强调。
- `<u>下划线</u>`：核心判断句。
- `==高亮==`：短关键词。
- `<span style="color:#306998"><strong>关键词</strong></span>`：需要颜色提示的重点词。

## Callout 信息优先级

- `> [!summary]`：一句话结论。
- `> [!important]`：核心公式或必须记住的判断。
- `> [!warning]`：风险、弱点、注意事项。
- `> [!danger]`：关键矛盾或严重问题。
- `> [!tip]`：改进建议。
- `> [!success]`：优点、亮点、可保留内容。

## Python 色系规范

当用户要求"像 Python 一样""按 Python 颜色""关键词加颜色"时，使用完整 Python Logo 色系。

| 用途 | 颜色名 | HEX | 建议用途 |
|---|---|---|---:|
| 浅蓝 | Cyan-blue Azure | `#4B8BBE` | 架构、能力、模式、协作机制 |
| 深蓝 | Lapis Lazuli | `#306998` | AI / Agent / API / 平台 / 工具名等主术语 |
| 浅黄 | Shandy | `#FFE873` | 输出物、文档、HTML、prompt、rubric、示例 |
| 深黄 | Sunglow | `#FFD43B` | 上下文、记忆、工作流、安全治理、关键机制 |
| 灰色 | Granite Gray | `#646464` | 补充说明、弱强调、元信息 |

推荐写法：

```md
<span style="color:#306998"><strong>关键词</strong></span>
```

浅黄 `#FFE873` 和深黄 `#FFD43B` 在浅色主题里可能对比不足。需要保证可读性时，优先用背景色写法：

```md
<span style="background-color:#FFE873;color:#1f2937;padding:0 2px;border-radius:3px"><strong>关键词</strong></span>
```

不要每行都上色；只给关键技术术语、核心概念、重要输出物和风险/治理词上色。
