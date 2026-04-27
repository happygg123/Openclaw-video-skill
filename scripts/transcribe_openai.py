#!/usr/bin/env python3
"""
OpenAI Whisper API 转写脚本
支持超长视频自动切片转写

使用方法:
    python3 transcribe_openai.py <video_or_audio_path> [--output output.json]

环境变量:
    OPENAI_API_KEY - 必填，也可从 ~/.openclaw/openclaw.json 自动读取
"""

import os
import sys
import json
import math
import subprocess
import argparse
from pathlib import Path

try:
    import openai
except ImportError:
    print("错误: 未安装 openai 库，请先执行: pip install openai")
    sys.exit(1)


def load_api_key():
    """自动从环境变量或 OpenClaw 配置文件读取 API Key"""
    key = os.environ.get("OPENAI_API_KEY")
    if key:
        return key

    config_paths = [
        Path.home() / ".openclaw" / "openclaw.json",
        Path.home() / ".openclaw" / "config.json",
    ]
    for p in config_paths:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    config = json.load(f)
                # 尝试常见的 key 路径
                for path in ["apiKey", "openai.apiKey", "models.providers.openai.apiKey"]:
                    parts = path.split(".")
                    val = config
                    for part in parts:
                        val = val.get(part, {}) if isinstance(val, dict) else None
                    if val and isinstance(val, str) and val.startswith("sk-"):
                        return val
            except Exception:
                pass
    return None


def get_duration(filepath):
    """获取媒体时长（秒）"""
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(filepath),
        ],
        capture_output=True, text=True,
    )
    return float(result.stdout.strip())


def extract_audio_segment(video_path, output_path, start=0, duration=None):
    """提取音频片段"""
    cmd = [
        "ffmpeg", "-y", "-i", str(video_path),
        "-vn",
        "-ar", "16000", "-ac", "1",
        "-acodec", "libmp3lame", "-b:a", "32k",
    ]
    if start > 0:
        cmd += ["-ss", str(start)]
    if duration:
        cmd += ["-t", str(duration)]
    cmd += [str(output_path)]
    subprocess.run(cmd, check=True, capture_output=True)


def transcribe_segment(client, audio_path, start_offset=0):
    """调用 OpenAI Whisper API 转写单个音频"""
    with open(audio_path, "rb") as f:
        response = client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="zh",
            response_format="verbose_json",
            timestamp_granularities=["word"],
        )

    data = response.to_dict()

    # 修正时间偏移
    if start_offset > 0:
        for seg in data.get("segments", []):
            seg["start"] += start_offset
            seg["end"] += start_offset
        for word in data.get("words", []):
            word["start"] += start_offset
            word["end"] += start_offset

    return data


def transcribe_video(video_path, output_json, segment_sec=300):
    """主函数：转写视频，支持自动切片"""
    api_key = load_api_key()
    if not api_key:
        print("错误: 未找到 OPENAI_API_KEY，请设置环境变量或在配置文件中指定")
        sys.exit(1)

    client = openai.OpenAI(api_key=api_key)
    video_path = Path(video_path)

    if not video_path.exists():
        print(f"错误: 文件不存在: {video_path}")
        sys.exit(1)

    duration = get_duration(video_path)
    print(f"视频时长: {duration:.1f}s")

    # 检查是否需要切片（25MB 限制，音频约 0.2MB/秒按 32kbps 算）
    safe_segment_sec = min(segment_sec, 1200)  # 最大 20 分钟一片

    all_segments = []
    all_words = []
    all_text_parts = []

    num_segments = math.ceil(duration / safe_segment_sec)
    print(f"分割为 {num_segments} 段进行转写...")

    for i in range(num_segments):
        start = i * safe_segment_sec
        seg_duration = min(safe_segment_sec, duration - start)
        print(f"  处理第 {i+1}/{num_segments} 段 ({start:.0f}s ~ {start+seg_duration:.0f}s)...")

        tmp_audio = f"/tmp/whisper_seg_{i}_{video_path.stem}.mp3"
        extract_audio_segment(video_path, tmp_audio, start, seg_duration)

        result = transcribe_segment(client, tmp_audio, start_offset=start)
        all_segments.extend(result.get("segments", []))
        all_words.extend(result.get("words", []))
        all_text_parts.append(result.get("text", ""))

        # 清理临时文件
        Path(tmp_audio).unlink(missing_ok=True)

    # 合并输出
    output = {
        "task": "transcribe",
        "language": "zh",
        "duration": duration,
        "text": "\n".join(all_text_parts),
        "segments": all_segments,
        "words": all_words,
    }

    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n✓ 转写完成: {output_json}")
    print(f"  总字符数: {len(output['text'])}")
    print(f"  词级条目: {len(all_words)}")
    print(f"  段级条目: {len(all_segments)}")

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OpenAI Whisper API 语音转写")
    parser.add_argument("input", help="输入视频或音频文件路径")
    parser.add_argument("-o", "--output", default="transcript.json", help="输出 JSON 路径 (default: transcript.json)")
    parser.add_argument("--segment", type=int, default=300, help="单段最长秒数 (default: 300)")
    args = parser.parse_args()

    transcribe_video(args.input, args.output, args.segment)
