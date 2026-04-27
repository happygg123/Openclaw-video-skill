---
name: telegram-video-split-caption-bgm
description: 从 Telegram 入站视频快速产出 3-4 条竖版短视频，支持中文轮播字幕、美观底框、分片不同背景音乐，并回传成片。
---

# 适用场景
- 用户在 Telegram 里发来视频，要求“直接出成片”。
- 需要拆成 3-4 条短视频，并加中文文案。
- 需要迭代调样式（字幕位置、轮播、音乐风格）。

# 关键经验（本次验证）
1. **先找文件落地位置**：在当前环境，Telegram 视频常落在：
   - `/home/ubuntu/.openclaw/media/inbound/`
2. 常规目录（`/home/ubuntu`、`/tmp`）可能检索不到，容易误判“用户没发”。
3. 中文字幕用 `wqy-zenhei.ttc` 稳定：
   - `/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc`
4. 视觉上更好看：字幕底框放在**中下区域**，必要时微调上移约 1%。
5. 用户常要求“别单调”：要做**多段轮播文案** + **每条不同BGM**。

# 标准流程
1. 定位入站视频
   - 用文件搜索先查 `.mp4/.mov/.webm`。
   - 重点查 `/home/ubuntu/.openclaw/media/inbound/`。
2. 备份原视频到稳定目录
   - 例如：`/home/ubuntu/video_jobs/<job_id>/source.mp4`
3. 用 ffprobe 获取时长与尺寸
   - 确认是否竖版（如 464x848）和分片时长。
4. 先拆分 3-4 段（每段约 15-20 秒）
5. 二次渲染每段：
   - `drawbox` 半透明底框
   - `drawtext` 三段轮播（`enable='between(t,a,b)'`）
   - 主副文字层级（白/金色）
   - `stream_loop` + `amix` 混入 BGM，音量低于原声
6. 回传并根据反馈做微调
   - 常见微调：底框上移、字号、行距、节奏、换歌。
   - 重要：如果用户说 Telegram 把视频压缩了，需把成片（必要时连封面一起）打成 `.zip` 再发送，避免平台按视频媒体重新压缩。
   - 在当前环境即使直接发送 MP4，Telegram 也可能按视频处理并压缩；ZIP 交付更稳。
   - 若用户强调“不要压缩原视频 / 保持像素”，导出时优先保持原始画面信息不被二次缩小：不要降分辨率、不要额外强压缩；如需统一竖版尺寸，明确保持目标成片为用户要求分辨率（如 1080x1920），并用 ZIP 或直链交付原始像素版本。
   - 若是“口播优化”而不是“重写包装”，优先保留原视频完整性：不要大幅删停顿，不要把口播改写成文案腔。除非同一句话连续重复两遍，否则尽量不剪内容。
   - 字幕默认策略：只纠正明显错别字/识别错误，尽量保持原话，不擅自精简改写；否则很容易与用户预期不符。
   - 节奏剪辑一旦涉及删段，必须重点验音画同步。优先只删完整重复句，导出后检查成片总时长是否接近原片，避免观感像“断片”。
   - 口播样板规则（已验证）：
     1. 首页视觉可以颜色更重，允许高饱和红/黄等强对比色；标题必须大，先抓眼球。
     2. 字幕位置通常放在下三分之一附近，约画面高度 57%~60% 起，不要太贴底，也不要挡脸。
     3. 字幕样式以白字黑边为主，关键词少量高亮即可；重点是稳、清楚、不乱跳。
     4. 大字报可以很吸睛，但不要破坏原画面主体；优先做短促闪现，而不是长时间遮挡。
   - 若用户给了“口播样板”，先对齐样板再动手：重点看首页视觉、字幕位置、字幕大小、是否避脸，再做重渲染，避免按自己的审美乱改。
   - 用户这类口播常见偏好：首页视觉可以很重，颜色要强对比、字体要够大够炸裂；但字幕区要稳定，通常从下三分之一附近开始（约画面高度 57%~60%），不要贴太底，也不要飘到中间挡脸。
   - 首页大字报与正文字幕是两套逻辑：开头 0.2~0.4 秒可以用高饱和红/黄等重色块+超大字吸睛；正文字幕仍然保持白字黑边、位置固定、以可读性优先。

# FFmpeg 模板（单段）
```bash
ffmpeg -y \
  -stream_loop -1 -i /path/to/bgm.ogg \
  -i /path/to/clip.mp4 \
  -filter_complex "
[0:a]aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo,
      volume=0.12,atempo=1.04,atrim=0:15.8,
      afade=t=in:st=0:d=0.9,afade=t=out:st=14.2:d=1.3[bgm];
[1:a]volume=0.92[a0];
[a0][bgm]amix=inputs=2:duration=first:dropout_transition=1[a];
[1:v]
 drawbox=x=20:y=548:w=424:h=220:color=black@0.36:t=fill,
 drawtext=fontfile=/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc:text='主标题':fontsize=34:fontcolor=white:borderw=2:bordercolor=black@0.6:x=(w-text_w)/2:y=578:enable='between(t,0,5.2)',
 drawtext=fontfile=/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc:text='副标题1':fontsize=27:fontcolor=0xF7D154:borderw=2:bordercolor=black@0.6:x=(w-text_w)/2:y=628:enable='between(t,0,5.2)',
 drawtext=fontfile=/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc:text='副标题2':fontsize=27:fontcolor=white:borderw=2:bordercolor=black@0.6:x=(w-text_w)/2:y=678:enable='between(t,0,5.2)'
[v]" \
  -map "[v]" -map "[a]" \
  -c:v libx264 -preset veryfast -crf 21 -c:a aac -shortest \
  /path/to/clip_pretty.mp4
```

# 热闹风 BGM 选择（两级方案）

## 方案A：系统内置（最快）
- `/usr/share/sounds/ubuntu/ringtones/Latin.ogg`
- `/usr/share/sounds/ubuntu/ringtones/Sparkle.ogg`
- `/usr/share/sounds/ubuntu/ringtones/Counterpoint.ogg`
- `/usr/share/sounds/ubuntu/ringtones/Supreme.ogg`

> 仅适合快速打样。若用户反馈“像铃声/不高级”，要立即切方案B。

## 方案B：直接用 Mixkit 歌曲（更像短视频成片）
关键经验：可不走浏览器下载，直接通过下载弹窗接口拿到 mp3。

1) 先拿某个音乐条目的下载链接（格式通常是）：
- `https://mixkit.co/free-stock-music/download/<id>/?context=item+grid`

2) 该页面里会给出真实 mp3：
- `https://assets.mixkit.co/music/<id>/<id>.mp3`

3) 可直接批量下载：
```bash
mkdir -p /home/ubuntu/video_jobs/<job_id>/music_mixkit
for id in 250 288 200 801; do
  curl -L -o /home/ubuntu/video_jobs/<job_id>/music_mixkit/$id.mp3 \
    "https://assets.mixkit.co/music/$id/$id.mp3"
done
```

4) 混音建议（保留原声 + 歌曲）：
- 歌曲音量先从 `0.22~0.26` 起步
- 原声保持 `0.9~0.95`
- 用 `afade` 做首尾淡入淡出
- `alimiter` 防止爆音

示例：
```bash
ffmpeg -y -i clip_with_text.mp4 -i song.mp3 \
  -filter_complex "
[0:a]volume=0.95[a0];
[1:a]volume=0.24,atrim=0:15.8,
      afade=t=in:st=0:d=0.7,
      afade=t=out:st=14.5:d=0.9[a1];
[a0][a1]amix=inputs=2:duration=first:dropout_transition=1,
alimiter=limit=0.92[a]
" \
  -map 0:v -map "[a]" -c:v copy -c:a aac -shortest out.mp4
```

建议每条片子用不同曲目，避免“全片同味”。

# 验收清单
- 4 条输出文件都存在且可播放。
- 每条都有轮播字幕，不是单块静态牌子。
- 底框位置美观（中下，无遮挡主体）。
- BGM 与人声混音平衡，听得清原声。
- 时长与原分片接近，无明显音画不同步。

# 收尾清理（用户要求“只是练习，全部删除”时）
若用户明确要求删除素材，需执行闭环清理并复查：

1) 删除入站原片与输出目录（按实际路径替换）：
```bash
rm -f /home/ubuntu/.openclaw/media/inbound/<source>.mp4
rm -f /home/ubuntu/.openclaw/workspace/video_output/pakistan_biz_*.mp4
rm -rf /home/ubuntu/video_jobs/<job_id>
```

2) 复查确认：
```bash
# job 目录是否清空
search_files(target='files', pattern='*<job_id>*', path='/home/ubuntu')
# 原片是否清空
search_files(target='files', pattern='<source>*', path='/home/ubuntu/.openclaw/media/inbound')
```

3) 给用户明确回执：
- 原始来稿已删除
- 全部中间文件已删除
- 全部导出成片已删除
