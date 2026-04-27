# OpenClaw Video Skill — 口播短视频自动化剪辑

适用于 [OpenClaw](https://github.com/openclaw) / Hermes Agent 的短视频剪辑 Skill。接收 Telegram 入站视频，自动产出带字幕、BGM、封面的竖版短视频成片。

## ✨ 能力

- **语音转字幕**：支持 **OpenAI Whisper API** 和 **faster-whisper** 本地转写两种方案
- **智能字幕**：白字黑边、下三分之一位置、关键词高亮
- **封面大字报**：高饱和配色（红/黄），短促闪现吸睛
- **BGM 混音**：原声保留 + 背景音乐，自动淡入淡出
- **无损交付**：ZIP 打包 + HTTP 直链，绕过平台压缩
- **口播专用**：只纠错不改写、不删停顿、仅删连续重复句

## 📦 安装

将本仓库内容放入 OpenClaw 的 skills 目录：

```bash
cp -r telegram-video-split-caption-bgm ~/.hermes/skills/media/
```

## 🔧 依赖

- FFmpeg（>= 4.4）
- Python 3.10+
- `openai` 或 `faster-whisper` 二选一
- 中文字体：`wqy-zenhei.ttc`

```bash
sudo apt install ffmpeg
pip install openai faster-whisper
```

## 🚀 标准流程

1. 用户发送视频 → 落盘到 `~/.openclaw/media/inbound/`
2. 语音转写（推荐用 OpenAI Whisper API）生成时间轴字幕
3. 校对字幕（只纠正错别字，不改写原话）
4. 生成 ASS 字幕文件（下三分之一位置）
5. FFmpeg 合成：视频 + 字幕 + BGM 混音
6. 封面大字报制作
7. ZIP 打包 → HTTP 直链交付

## 🎤 语音转写

### 方案 A：OpenAI Whisper API（推荐）

```bash
python3 scripts/transcribe_openai.py source.mp4 -o transcript.json
```

特点：
- 云端运行，不需要本地 GPU
- 支持超长视频自动切片转写
- 单文件限制 25MB，脚本自动处理

配置 API Key：
```bash
export OPENAI_API_KEY=sk-xxx
```

### 方案 B：faster-whisper（本地）

```python
from faster_whisper import WhisperModel
model = WhisperModel("small", device="cpu")
segments, _ = model.transcribe("source.mp4")
```

## 🎨 视觉标准

| 项目 | 规范 |
|------|------|
| 字幕位置 | 画面高度 57%~60% 起（下三分之一） |
| 字幕样式 | 白字 + 黑边，关键词少量高亮 |
| 封面 | 高饱和红/黄，超大字号，短促闪现 |
| 交付 | ZIP 打包原始像素，HTTP 直链下载 |

## 📄 完整规范

详见 [SKILL.md](./SKILL.md)

## 📜 License

MIT
