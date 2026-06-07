#!/usr/bin/env python3
"""Fetch YouTube transcripts and convert them into Markdown."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SKILL_ROOT = Path(__file__).resolve().parents[1]


def default_output_dir() -> Path:
    env_dir = os.environ.get("YOUTUBE_MD_OUTPUT_DIR")
    if env_dir:
        return Path(env_dir).expanduser()

    local_config = SKILL_ROOT / ".output-dir.local"
    if local_config.exists():
        value = local_config.read_text(encoding="utf-8").strip()
        if value:
            return Path(value).expanduser()

    return Path("outputs")


DEFAULT_OUTPUT_DIR = default_output_dir()

DEFAULT_LANGUAGES = [
    "zh-Hans",
    "zh-CN",
    "zh",
    "zh-Hant",
    "zh-TW",
    "en",
]

VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL")


class TranscriptError(RuntimeError):
    """User-facing failure with a clear reason."""


@dataclass
class Cue:
    start: float
    duration: float
    text: str

    @property
    def end(self) -> float:
        return self.start + self.duration


@dataclass
class TranscriptResult:
    video_id: str
    language: str
    language_code: str
    is_generated: bool | None
    cues: list[Cue]
    source: str = "youtube-transcript-api"


def extract_video_id(value: str) -> str:
    value = value.strip()
    if VIDEO_ID_RE.match(value):
        return value

    parsed = urllib.parse.urlparse(value)
    host = parsed.netloc.lower()
    path_parts = [part for part in parsed.path.split("/") if part]

    if "youtu.be" in host and path_parts:
        video_id = path_parts[0]
    elif "youtube.com" in host or "youtube-nocookie.com" in host:
        query = urllib.parse.parse_qs(parsed.query)
        if query.get("v"):
            video_id = query["v"][0]
        elif path_parts and path_parts[0] in {"shorts", "embed", "live"} and len(path_parts) > 1:
            video_id = path_parts[1]
        else:
            video_id = ""
    else:
        video_id = ""

    if not VIDEO_ID_RE.match(video_id):
        raise TranscriptError("链接里没有解析到有效的 YouTube video_id。")
    return video_id


def normalize_title(title: str) -> str:
    title = title.strip()
    title = re.sub(r'[\\/:*?"<>|]+', "-", title)
    title = re.sub(r"\s+", " ", title).strip(" .")
    return title or "YouTube字幕整理"


def fetch_title(video_id: str) -> str:
    try:
        import requests
    except ImportError:
        return video_id

    url = "https://www.youtube.com/oembed"
    try:
        response = requests.get(
            url,
            params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"},
            timeout=12,
        )
        if response.status_code != 200:
            return video_id
        data = response.json()
    except Exception:
        return video_id

    return normalize_title(str(data.get("title") or video_id))


def normalize_languages(values: list[str] | None) -> list[str]:
    if not values:
        return DEFAULT_LANGUAGES
    languages: list[str] = []
    for value in values:
        for part in value.split(","):
            part = part.strip()
            if part:
                languages.append(part)
    return languages or DEFAULT_LANGUAGES


def fetch_transcript(
    video_id: str,
    languages: list[str],
    translate_to: str | None = None,
    preserve_formatting: bool = False,
) -> TranscriptResult:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api._errors import (
            AgeRestricted,
            CouldNotRetrieveTranscript,
            NoTranscriptFound,
            TranscriptsDisabled,
            VideoUnavailable,
        )
    except ImportError as exc:
        raise TranscriptError(
            "缺少依赖 youtube-transcript-api。请先运行：python3 -m pip install --user youtube-transcript-api"
        ) from exc

    try:
        api = YouTubeTranscriptApi()
        if translate_to:
            transcript_list = api.list(video_id)
            transcript = transcript_list.find_transcript(languages).translate(translate_to)
            fetched = transcript.fetch(preserve_formatting=preserve_formatting)
        else:
            fetched = api.fetch(
                video_id,
                languages=languages,
                preserve_formatting=preserve_formatting,
            )
    except NoTranscriptFound as exc:
        raise TranscriptError(f"没有找到匹配语言的字幕：{', '.join(languages)}。") from exc
    except TranscriptsDisabled as exc:
        raise TranscriptError("这个视频关闭了字幕。") from exc
    except VideoUnavailable as exc:
        raise TranscriptError("这个视频不可用或无法访问。") from exc
    except AgeRestricted as exc:
        raise TranscriptError("这个视频有年龄限制；当前库文档说明 Cookie 鉴权不稳定，暂不默认处理。") from exc
    except CouldNotRetrieveTranscript as exc:
        raise TranscriptError(f"无法获取字幕：{exc}") from exc

    raw_items = fetched.to_raw_data()
    cues = [
        Cue(
            start=float(item.get("start", 0.0)),
            duration=float(item.get("duration", 0.0)),
            text=clean_inline_text(str(item.get("text", ""))),
        )
        for item in raw_items
    ]
    cues = [cue for cue in cues if cue.text]
    if not cues:
        raise TranscriptError("字幕数据为空，无法生成 Markdown。")

    return TranscriptResult(
        video_id=video_id,
        language=str(getattr(fetched, "language", "")) or "unknown",
        language_code=str(getattr(fetched, "language_code", "")) or "unknown",
        is_generated=bool(getattr(fetched, "is_generated", False)),
        cues=cues,
    )


def fetch_transcript_with_fallback(
    video_id: str,
    languages: list[str],
    translate_to: str | None = None,
    preserve_formatting: bool = False,
    yt_dlp_only: bool = False,
    use_yt_dlp_fallback: bool = True,
) -> TranscriptResult:
    primary_error: TranscriptError | None = None

    if not yt_dlp_only:
        try:
            return fetch_transcript(
                video_id=video_id,
                languages=languages,
                translate_to=translate_to,
                preserve_formatting=preserve_formatting,
            )
        except TranscriptError as exc:
            primary_error = exc
            if not use_yt_dlp_fallback:
                raise

    fallback_languages = [translate_to] if translate_to else languages
    try:
        return fetch_transcript_with_yt_dlp(video_id=video_id, languages=fallback_languages)
    except TranscriptError as exc:
        if primary_error:
            raise TranscriptError(
                f"youtube-transcript-api 获取失败：{primary_error}；yt-dlp 兜底也失败：{exc}"
            ) from exc
        raise


def fetch_transcript_with_yt_dlp(video_id: str, languages: list[str]) -> TranscriptResult:
    if not shutil.which("yt-dlp"):
        raise TranscriptError(
            "未找到 yt-dlp 命令。请先安装：brew install yt-dlp"
        )

    language_arg = ",".join(languages)
    url = f"https://www.youtube.com/watch?v={video_id}"
    with tempfile.TemporaryDirectory(prefix="youtube-md-ytdlp-") as tmpdir:
        command = [
            "yt-dlp",
            "--skip-download",
            "--no-playlist",
            "--write-subs",
            "--write-auto-subs",
            "--sub-langs",
            language_arg,
            "--sub-format",
            "vtt",
            "-P",
            tmpdir,
            "-o",
            "%(id)s.%(ext)s",
            url,
        ]
        completed = subprocess.run(
            command,
            check=False,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()
            raise TranscriptError(detail or "yt-dlp 没有成功下载字幕。")

        subtitle_files = sorted(Path(tmpdir).glob("*.vtt"))
        if not subtitle_files:
            raise TranscriptError("yt-dlp 没有写出 VTT 字幕文件。")

        subtitle_path, language_code = choose_subtitle_file(subtitle_files, video_id, languages)
        cues = parse_vtt_file(subtitle_path)
        if not cues:
            raise TranscriptError("yt-dlp 下载的字幕为空，无法生成 Markdown。")

    return TranscriptResult(
        video_id=video_id,
        language=language_code,
        language_code=language_code,
        is_generated=None,
        cues=cues,
        source="yt-dlp",
    )


def choose_subtitle_file(
    subtitle_files: list[Path],
    video_id: str,
    languages: list[str],
) -> tuple[Path, str]:
    ranked: list[tuple[int, int, Path, str]] = []
    for index, path in enumerate(subtitle_files):
        language_code = infer_language_code(path, video_id)
        score = len(languages) + 1
        for language_index, requested in enumerate(languages):
            if language_code == requested or language_code.startswith(f"{requested}-"):
                score = language_index
                break
        ranked.append((score, index, path, language_code))

    _, _, path, language_code = sorted(ranked)[0]
    return path, language_code


def infer_language_code(path: Path, video_id: str) -> str:
    stem = path.stem
    prefix = f"{video_id}."
    if stem.startswith(prefix):
        return stem[len(prefix) :] or "unknown"
    if "." in stem:
        return stem.rsplit(".", 1)[-1] or "unknown"
    return "unknown"


def parse_vtt_timestamp(value: str) -> float:
    value = value.replace(",", ".").strip()
    parts = value.split(":")
    if len(parts) == 3:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
    elif len(parts) == 2:
        hours = 0
        minutes = int(parts[0])
        seconds = float(parts[1])
    else:
        raise ValueError(f"Invalid VTT timestamp: {value}")
    return hours * 3600 + minutes * 60 + seconds


def clean_vtt_text(text: str) -> str:
    text = re.sub(r"<\d{2}:\d{2}:\d{2}\.\d{3}>", "", text)
    text = re.sub(r"<\d{2}:\d{2}\.\d{3}>", "", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return clean_inline_text(text)


def parse_vtt_file(path: Path) -> list[Cue]:
    lines = path.read_text(encoding="utf-8-sig", errors="replace").splitlines()
    cues: list[Cue] = []
    index = 0

    while index < len(lines):
        line = lines[index].strip()
        if "-->" not in line:
            index += 1
            continue

        start_token, end_part = line.split("-->", 1)
        end_token = end_part.strip().split()[0]
        try:
            start = parse_vtt_timestamp(start_token)
            end = parse_vtt_timestamp(end_token)
        except ValueError:
            index += 1
            continue

        index += 1
        text_lines: list[str] = []
        while index < len(lines) and lines[index].strip():
            text_lines.append(lines[index].strip())
            index += 1

        text = clean_vtt_text(" ".join(text_lines))
        if text:
            cues.append(Cue(start=start, duration=max(0.0, end - start), text=text))

    return dedupe_cues(cues)


def dedupe_cues(cues: list[Cue]) -> list[Cue]:
    deduped: list[Cue] = []
    for cue in cues:
        if deduped and cue.text == deduped[-1].text:
            continue
        if deduped and cue.start < deduped[-1].end and cue.text.startswith(deduped[-1].text):
            previous = deduped[-1]
            deduped[-1] = Cue(
                start=previous.start,
                duration=max(previous.duration, cue.end - previous.start),
                text=cue.text,
            )
            continue
        deduped.append(cue)
    return deduped


def clean_inline_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def split_sentences(text: str) -> list[str]:
    pieces = re.split(r"(?<=[。！？!?；;.!?])\s*", text)
    return [piece.strip() for piece in pieces if piece.strip()]


def cues_to_paragraphs(cues: list[Cue]) -> list[str]:
    sentences: list[str] = []
    buffer = ""

    for cue in cues:
        text = cue.text
        if not text:
            continue

        if buffer:
            if re.match(r"^[，。！？!?；;、：:）)\]】,.!?]", text):
                buffer += text
            else:
                buffer += text if buffer.endswith(("，", "、", "：", ":", ",")) else " " + text
        else:
            buffer = text

        extracted = split_sentences(buffer)
        if extracted and re.search(r"[。！？!?；;.!?]$", buffer):
            sentences.extend(extracted)
            buffer = ""
        elif len(buffer) >= 140:
            sentences.append(buffer.strip())
            buffer = ""

    if buffer.strip():
        sentences.append(buffer.strip())

    paragraphs: list[str] = []
    current: list[str] = []
    char_count = 0

    for sentence in sentences:
        current.append(sentence)
        char_count += len(sentence)
        if char_count >= 260 or len(current) >= 6:
            paragraphs.append("".join(current).strip())
            current = []
            char_count = 0

    if current:
        paragraphs.append("".join(current).strip())

    return [paragraph for paragraph in paragraphs if paragraph]


def seconds_to_display(value: float) -> str:
    total_seconds = max(0, int(value))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


def seconds_to_srt_time(value: float) -> str:
    total_ms = max(0, int(round(value * 1000)))
    hours, remainder = divmod(total_ms, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    seconds, ms = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d},{ms:03d}"


def build_time_draft(cues: list[Cue], target_sections: int = 8) -> list[str]:
    section_count = min(target_sections, max(1, len(cues) // 24 or 1))
    chunk_size = max(1, len(cues) // section_count)
    lines: list[str] = []

    for i in range(0, len(cues), chunk_size):
        chunk = cues[i : i + chunk_size]
        if not chunk:
            continue
        start = seconds_to_display(chunk[0].start)
        end = seconds_to_display(chunk[-1].end)
        sample = " ".join(cue.text for cue in chunk[:5])[:70].strip()
        lines.append(f"- {start}-{end} 待整理章节：{sample}")

    return lines


def transcript_to_markdown(
    result: TranscriptResult,
    title: str,
    keep_time: bool,
    include_meta: bool,
) -> str:
    paragraphs = cues_to_paragraphs(result.cues)
    if not paragraphs:
        raise TranscriptError("字幕里没有可写入 Markdown 的正文内容。")

    parts = [f"# {normalize_title(title)}"]
    if include_meta:
        if result.is_generated is None:
            generated = "未知"
        else:
            generated = "自动字幕" if result.is_generated else "人工字幕"
        parts.extend(
            [
                f"- Video ID: `{result.video_id}`",
                f"- 字幕语言: {result.language} (`{result.language_code}`)",
                f"- 字幕类型: {generated}",
                f"- 字幕来源: {result.source}",
            ]
        )
    parts.extend(paragraphs)

    if keep_time:
        parts.extend(["## 时间目录", *build_time_draft(result.cues)])

    return "\n\n".join(parts).strip() + "\n"


def transcript_to_srt(cues: list[Cue]) -> str:
    blocks: list[str] = []
    for index, cue in enumerate(cues, start=1):
        blocks.append(
            "\n".join(
                [
                    str(index),
                    f"{seconds_to_srt_time(cue.start)} --> {seconds_to_srt_time(cue.end)}",
                    cue.text,
                ]
            )
        )
    return "\n\n".join(blocks).strip() + "\n"


def transcript_to_json(result: TranscriptResult) -> str:
    payload: dict[str, Any] = {
        "video_id": result.video_id,
        "language": result.language,
        "language_code": result.language_code,
        "is_generated": result.is_generated,
        "body": [
            {"start": cue.start, "duration": cue.duration, "text": cue.text}
            for cue in result.cues
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def unique_output_path(output_dir: Path, title: str, suffix: str) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    safe_title = normalize_title(title)
    candidate = output_dir / f"{safe_title}{suffix}"
    if not candidate.exists():
        return candidate

    counter = 2
    while True:
        candidate = output_dir / f"{safe_title}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def run(args: argparse.Namespace) -> int:
    video_id = extract_video_id(args.url)
    languages = normalize_languages(args.languages)
    title = normalize_title(args.title or fetch_title(video_id))
    result = fetch_transcript_with_fallback(
        video_id=video_id,
        languages=languages,
        translate_to=args.translate_to,
        preserve_formatting=args.preserve_formatting,
        yt_dlp_only=args.yt_dlp_only,
        use_yt_dlp_fallback=not args.no_yt_dlp_fallback,
    )

    output_dir = Path(args.output_dir).expanduser()
    json_path: Path | None = None
    srt_path: Path | None = None

    if args.save_json:
        json_path = unique_output_path(output_dir, title, ".json")
        json_path.write_text(transcript_to_json(result), encoding="utf-8")

    if args.save_srt:
        srt_path = unique_output_path(output_dir, title, ".srt")
        srt_path.write_text(transcript_to_srt(result.cues), encoding="utf-8")

    md_path = unique_output_path(output_dir, title, ".md")
    md_path.write_text(
        transcript_to_markdown(result, title, args.keep_time, args.include_meta),
        encoding="utf-8",
    )

    print(f"视频：{title}")
    print(f"Video ID：{video_id}")
    print(f"字幕：{result.language} ({result.language_code})")
    if result.is_generated is None:
        print("类型：未知")
    else:
        print(f"类型：{'自动字幕' if result.is_generated else '人工字幕'}")
    print(f"来源：{result.source}")
    if json_path:
        print(f"JSON：{json_path}")
    if srt_path:
        print(f"SRT：{srt_path}")
    print(f"Markdown：{md_path}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch YouTube transcripts and convert them to Markdown."
    )
    parser.add_argument("--url", required=True, help="YouTube video URL or 11-char video ID.")
    parser.add_argument("--title", help="Optional title override for Markdown H1 and filename.")
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory where output files should be saved.",
    )
    parser.add_argument(
        "--languages",
        nargs="*",
        help="Preferred transcript language codes, e.g. zh-Hans zh-CN zh en.",
    )
    parser.add_argument(
        "--translate-to",
        help="Translate a found transcript to this language code, e.g. zh-Hans or en.",
    )
    parser.add_argument(
        "--keep-time",
        action="store_true",
        help="Append a rough time directory to the Markdown.",
    )
    parser.add_argument(
        "--include-meta",
        action="store_true",
        help="Include transcript language/type metadata below the title.",
    )
    parser.add_argument(
        "--preserve-formatting",
        action="store_true",
        help="Ask youtube-transcript-api to preserve basic subtitle formatting.",
    )
    parser.add_argument(
        "--no-yt-dlp-fallback",
        action="store_true",
        help="Disable yt-dlp fallback when youtube-transcript-api fails.",
    )
    parser.add_argument(
        "--yt-dlp-only",
        action="store_true",
        help="Fetch subtitles with yt-dlp directly instead of youtube-transcript-api.",
    )
    parser.add_argument("--save-json", action="store_true", help="Save transcript JSON for debugging.")
    parser.add_argument("--save-srt", action="store_true", help="Save converted SRT for debugging.")
    return parser


def main(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return run(args)
    except TranscriptError as exc:
        print(f"失败：{exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
