# YouTube Transcript to Markdown

把 YouTube 视频字幕整理成适合 Obsidian 阅读的 Markdown 长文。

## 功能

- 支持 `youtube.com/watch?v=...`、`youtu.be/...`、`/shorts/...`、`/embed/...` 链接。
- 使用 `youtube-transcript-api` 获取人工字幕或自动字幕。
- 默认语言优先级：简体中文、繁体中文、英文。
- 可选保留时间信息，并生成时间目录草稿。
- 可选把字幕调试输出保存为 JSON 或 SRT。

## 安装依赖

```bash
python3 -m pip install --user youtube-transcript-api requests
```

## 使用方法

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

或者使用环境变量：

```bash
export YOUTUBE_MD_OUTPUT_DIR="/path/to/obsidian"
python3 scripts/youtube_transcript_to_md.py --url "https://www.youtube.com/watch?v=VIDEO_ID"
```

也可以在仓库根目录创建一个不会提交到 Git 的本地配置文件：

```bash
echo "/path/to/obsidian" > .output-dir.local
python3 scripts/youtube_transcript_to_md.py --url "https://www.youtube.com/watch?v=VIDEO_ID"
```

保留时间目录：

```bash
python3 scripts/youtube_transcript_to_md.py \
  --url "https://www.youtube.com/watch?v=VIDEO_ID" \
  --keep-time
```

## Codex Skill

这个仓库也是一个 Codex skill。把目录放入：

```text
~/.agents/skills/youtube-transcript-to-md
```

然后可以这样调用：

```text
Use $youtube-transcript-to-md 把这个 YouTube 视频链接整理成 Obsidian Markdown 长文。
```

## 限制

- 依赖 `youtube-transcript-api` 的非官方 transcript 机制，可能随 YouTube 改动而失效。
- 不需要 API key，也不默认使用 Cookie。
- 年龄限制、地区限制、关闭字幕或没有字幕的视频可能无法提取。
