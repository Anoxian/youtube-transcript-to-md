---
name: youtube-transcript-to-md
description: YouTube 链接转 Obsidian Markdown 长文：使用 youtube-transcript-api 获取 YouTube 人工字幕或自动字幕，优先中文再英文，默认只生成 Markdown 并保存到指定 Obsidian 目录；支持调试输出 JSON/SRT、保留时间目录和字幕笔记的渐进式排版优化。
---

# YouTube 字幕转 Obsidian 长文

## 目标

把用户给的 YouTube 视频链接转换为一篇可读的 Markdown 长文，并保存到 Obsidian 目录。默认只输出 Markdown，不保存 JSON 或 SRT 调试文件。

默认输出目录可通过环境变量 `YOUTUBE_MD_OUTPUT_DIR` 指定。也可以在 skill 根目录放一个不提交到 Git 的 `.output-dir.local` 文件保存本机默认输出目录。都未指定时，脚本会写入当前目录下的 `outputs/`：

`./outputs`

依赖：

`youtube-transcript-api`

可选兜底依赖：

`yt-dlp`

如果脚本提示缺少依赖，先运行：

```bash
python3 -m pip install --user youtube-transcript-api
```

如果 `youtube-transcript-api` 获取失败，脚本会自动尝试调用 `yt-dlp` 下载 VTT 字幕作为兜底。`yt-dlp` 推荐用 Homebrew 安装：

```bash
brew install yt-dlp
```

## 工作流

1. 从用户消息里提取 YouTube 链接或 11 位 video ID。
   - 支持 `youtube.com/watch?v=...`、`youtu.be/...`、`/shorts/...`、`/embed/...`。
   - 文件名优先使用 YouTube oEmbed 返回的视频标题；无法获得时使用 video ID。
2. 运行主脚本，直接生成 Markdown：

```bash
python3 <SKILL_ROOT>/scripts/youtube_transcript_to_md.py \
  --url "https://www.youtube.com/watch?v=..."
```

如果用户明确要求"保留时间""带时间""加时间目录"，再加：

```bash
--keep-time
```

平时不要加 `--save-json` 或 `--save-srt`。这两个参数只用于调试、核对字幕原始内容，日常交付只需要 Markdown。

默认流程是先用 `youtube-transcript-api`，失败时自动用 `yt-dlp` 兜底。遇到已知 API 抓不到、需要直接测试 `yt-dlp` 的视频，可以加：

```bash
--yt-dlp-only
```

如果需要禁用兜底，只测试主 API，可以加：

```bash
--no-yt-dlp-fallback
```

3. 默认语言优先级：

```text
zh-Hans -> zh-CN -> zh -> zh-Hant -> zh-TW -> en
```

如果用户指定语言，使用：

```bash
--languages en zh-Hans
```

如果用户要求把英文字幕翻译成中文，可使用：

```bash
--languages en --translate-to zh-Hans
```

4. 交付前必须检查：
   - 目标 Obsidian 目录里的 Markdown 是否存在。
   - 文件大小是否合理。
   - 抽查开头是否从视频开场字幕开始，避免漏掉前半段。
   - 最终回复只给 Markdown 路径，不需要展示 JSON/SRT。


## 脚本说明

主脚本路径：

`<SKILL_ROOT>/scripts/youtube_transcript_to_md.py`

常用参数：

- `--url`：YouTube 视频链接或 11 位 video ID。
- `--title`：手动指定标题和文件名。
- `--output-dir`：输出目录；优先级高于环境变量 `YOUTUBE_MD_OUTPUT_DIR` 和 `.output-dir.local`。
- `--languages`：语言优先级列表。
- `--translate-to`：把已找到的字幕翻译成目标语言。
- `--keep-time`：保留时间信息，并在末尾生成待人工整理的时间目录草稿。
- `--include-meta`：在标题下附加字幕语言、字幕类型等元信息。
- `--no-yt-dlp-fallback`：禁用 `yt-dlp` 自动兜底。
- `--yt-dlp-only`：跳过 `youtube-transcript-api`，直接用 `yt-dlp` 获取字幕。
- `--save-json`：调试用，保存 transcript JSON。
- `--save-srt`：调试用，保存转换后的 SRT。

脚本会避免覆盖已有 Markdown：同名文件存在时自动追加 `-2`、`-3`。

## 失败处理

- 成功时，直接交付 Markdown 路径。
- 没有字幕、字幕关闭、视频不可访问、年龄/地区限制时，不编造内容，直接说明失败原因。
- 缺少依赖时，提示安装 `youtube-transcript-api`。
- 主 API 失败时自动尝试 `yt-dlp`；如果本机没装 `yt-dlp`，提示安装 `brew install yt-dlp` 或 `python3 -m pip install --user yt-dlp`。
- 如果用户要求处理现成 SRT，可改用 B 站字幕 skill 里的 SRT 兜底脚本，或请用户提供字幕文本。

## 正文整理规则

- 不总结、不扩写、不把字幕改写成文章观点。
- 保留原文表达，只处理可读性：合并过短碎句、修正明显断行、按话题分段。
- 删除字幕序号和正文里的时间轴。
- 中文段落不要每句单独一行；英文段落也不要每个 transcript snippet 单独一行。
- 明显口误、重复语气词可以轻微整理，但不要改变意思。
- 输出 Markdown 顶部使用一级标题：`# 视频标题`。

## 时间目录规则

仅当用户明确说"保留时间""带时间""加时间目录"等时追加。目录放在文章末尾：

```md
## 时间目录

- 00:00-03:20 开场与本期问题：...
- 03:20-08:45 核心观点展开：...
```

要求：

- 先读完整字幕内容，理解视频自然分成哪些主题章节。
- 不机械按固定分钟切段。
- 每条都写成"时间段 + 章节标题：这一段讲了什么"。
- 时间段来自字幕起止时间；章节标题和说明来自你对内容的理解。
- 如果脚本先生成了粗糙时间块，必须人工合并、改名、重排成真正的内容目录。

## 排版优化（按需触发）

默认不要执行本步骤。只有当用户在字幕 Markdown 已生成后，明确说出类似"优化排版""突出重点""找不到重点""全是文字太乱""关键字加颜色""加点层级""加粗""斜体""下划线"等提示词时，才开始排版优化。

排版优化的目标不是重新提取字幕，而是把已经生成的长文整理成更适合 Obsidian 阅读的结构化笔记。

详细规则见 [排版优化指南](references/enhancement-guide.md)。
