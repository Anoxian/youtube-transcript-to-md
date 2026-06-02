# YouTube Transcript to Markdown

把 YouTube 视频字幕整理成适合 Obsidian 阅读的 Markdown 长文。这个仓库既可以作为独立 Python 脚本使用，也可以作为 Codex skill 使用。

## 它解决什么问题

很多 YouTube 视频有字幕，但直接复制出来通常是碎句、断行、时间轴和口语重复混在一起，不适合放进 Obsidian 阅读。这个 skill 的默认目标是：

- 从 YouTube 链接或 11 位 video ID 获取字幕。
- 优先中文，其次英文。
- 把字幕整理成一篇可读的 Markdown 长文。
- 默认只生成 Markdown，不保存调试用 JSON/SRT。
- 按需保留时间信息，生成时间目录草稿。
- 按需进入第二层排版优化，把长文整理成更清晰的 Obsidian 笔记。

## 两层工作流

### 第一层：字幕转 Markdown

这是默认流程。用户给出 YouTube 链接后，skill 直接运行脚本生成 Markdown。

适合这些请求：

```text
Use $youtube-transcript-to-md 把这个 YouTube 视频链接整理成 Obsidian Markdown 长文。
把这个 YouTube 视频转成 Markdown。
提取这个视频字幕，保存成 Obsidian 笔记。
```

第一层只做可读性整理：

- 合并过短碎句。
- 修正明显断行。
- 按话题自然分段。
- 删除字幕序号和正文里的时间轴。
- 不总结、不扩写、不把字幕改写成文章观点。

如果用户明确要求保留时间，例如“带时间”“保留时间”“加时间目录”，再开启 `--keep-time`。

### 第二层：渐进式排版优化

第二层不是默认执行，而是按需触发。只有当用户在字幕 Markdown 已生成后，明确提出类似这些要求时，才读取 `references/enhancement-guide.md`：

```text
优化排版
突出重点
关键字加颜色
全是文字太乱
找不到重点
加点层级
加粗
像 Python 一样给关键词配色
```

这就是本仓库的渐进式披露设计：平时不把排版规则塞进主流程，只有用户真的需要结构化阅读笔记时，才打开第二层参考指南。

第二层会把已经生成的 Markdown 进一步整理为更适合 Obsidian 阅读的笔记，例如：

- 用 `##`、`###`、编号章节和分隔线建立层级。
- 把密集对比改成表格。
- 把后续行动整理成 `- [ ]` 自查清单。
- 用 Obsidian callout 标出 summary、important、warning、tip 等信息。
- 对关键词适度使用加粗、斜体、下划线、高亮或颜色。
- 当用户要求 Python 风格配色时，使用 `references/enhancement-guide.md` 里的 Python Logo 色系。

## 仓库结构

```text
.
├── SKILL.md
├── README.md
├── LICENSE
├── agents/
│   └── openai.yaml
├── references/
│   └── enhancement-guide.md
└── scripts/
    └── youtube_transcript_to_md.py
```

- `SKILL.md`：Codex skill 的主说明，定义触发方式、默认流程和失败处理。
- `scripts/youtube_transcript_to_md.py`：主脚本，负责获取字幕并生成 Markdown。
- `references/enhancement-guide.md`：第二层排版优化指南，只在用户明确要求优化时读取。
- `agents/openai.yaml`：面向 OpenAI/Codex 运行环境的界面提示配置。

## 安装依赖

```bash
python3 -m pip install --user youtube-transcript-api requests
```

## 脚本用法

基础用法：

```bash
python3 scripts/youtube_transcript_to_md.py \
  --url "https://www.youtube.com/watch?v=VIDEO_ID"
```

指定输出目录：

```bash
python3 scripts/youtube_transcript_to_md.py \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --output-dir "/path/to/obsidian"
```

使用环境变量设置默认输出目录：

```bash
export YOUTUBE_MD_OUTPUT_DIR="/path/to/obsidian"
python3 scripts/youtube_transcript_to_md.py --url "https://www.youtube.com/watch?v=VIDEO_ID"
```

也可以在仓库根目录创建一个不会提交到 Git 的本地配置文件：

```bash
echo "/path/to/obsidian" > .output-dir.local
python3 scripts/youtube_transcript_to_md.py --url "https://www.youtube.com/watch?v=VIDEO_ID"
```

输出目录优先级：

```text
--output-dir > YOUTUBE_MD_OUTPUT_DIR > .output-dir.local > ./outputs
```

保留时间目录：

```bash
python3 scripts/youtube_transcript_to_md.py \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --keep-time
```

指定语言：

```bash
python3 scripts/youtube_transcript_to_md.py \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --languages zh-Hans zh-CN zh en
```

把英文字幕翻译成中文：

```bash
python3 scripts/youtube_transcript_to_md.py \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --languages en \
  --translate-to zh-Hans
```

调试时保存原始字幕：

```bash
python3 scripts/youtube_transcript_to_md.py \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --save-json \
  --save-srt
```

## 作为 Codex Skill 使用

把仓库放到本地 skills 目录：

```text
~/.agents/skills/youtube-transcript-to-md
```

然后可以这样调用：

```text
Use $youtube-transcript-to-md 把这个 YouTube 视频链接整理成 Obsidian Markdown 长文。
```

如果已经生成了一篇 Markdown，想进入第二层优化，可以继续说：

```text
把刚才生成的笔记优化排版，突出重点，关键词按 Python 色系加颜色。
```

这时 Codex 会读取 `references/enhancement-guide.md`，按里面的规则做结构化整理。

## 支持的链接格式

- `https://www.youtube.com/watch?v=...`
- `https://youtu.be/...`
- `https://www.youtube.com/shorts/...`
- `https://www.youtube.com/embed/...`
- 直接输入 11 位 YouTube video ID

## 默认语言优先级

```text
zh-Hans -> zh-CN -> zh -> zh-Hant -> zh-TW -> en
```

## 失败和限制

- 依赖 `youtube-transcript-api` 的非官方 transcript 机制，可能随 YouTube 改动而失效。
- 不需要 API key，也不默认使用 Cookie。
- 年龄限制、地区限制、关闭字幕或没有字幕的视频可能无法提取。
- YouTube 可能限制请求频率或封锁部分 IP。
- 本工具不会在字幕获取失败时编造内容。

参考项目：[jdepoix/youtube-transcript-api](https://github.com/jdepoix/youtube-transcript-api)

## License

MIT
