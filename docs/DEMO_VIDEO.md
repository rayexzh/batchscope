# BatchScope English demo / 英文演示材料

Version shown: **v0.5.0-alpha.2**. Duration: **2:49.75**. Format: **1920×1080, H.264 video + AAC audio, MP4**. English subtitles are burned into the picture; a separate SRT is supplied.

展示版本 v0.5.0-alpha.2，成片 2 分 49.75 秒，1080p。画面包含英文字幕，另附字幕文件与完整讲稿。

## Published downloads / 已发布下载

- [English captioned MP4 / 英文字幕视频](https://github.com/rayexzh/batchscope/releases/download/v0.5.0-alpha.2/BatchScope-English-Demo.mp4)
- [Complete demo and teacher-review pack / 完整材料包](https://github.com/rayexzh/batchscope/releases/download/v0.5.0-alpha.2/BatchScope-Demo-and-Teacher-Review.zip)
- [Release page / 发布页](https://github.com/rayexzh/batchscope/releases/tag/v0.5.0-alpha.2)

These are documentation assets for the existing application release; the Windows package remains unchanged. / 这些是当前版本的展示附件，Windows 软件包未改动。

## What the recording shows / 展示内容

The guided walkthrough covers synthetic-data generation, NULL-aware measurement metrics, underlying records, action follow-up, closed-parent follow-up, batch tracing, backlog ages, monthly reconciliation, two-date comparison and the offline report. All displayed values come from the real desktop prototype and fixed-seed fictional inputs.

视频覆盖生成数据、缺失值口径、记录复核、措施跟进、批次追踪、积压、月度对账、日期对比及离线报告。画面来自程序实际运行与固定种子虚构数据。

## Production disclosure / 制作方式

This is an edited walkthrough made from captured states of the native Tk application and its offline report, with chapter titles, highlights and captions. It is not an uninterrupted screen recording. The English voice is **Microsoft Zira Desktop**, synthesized locally on Windows at rate +2; it is not the maintainer speaking. No human teacher testimonial, employer result or real-company data is presented.

这是根据真实软件状态画面剪辑的引导演示，含章节、重点框和字幕；不是连续原始录屏。配音为本机合成英文声音，不是作者本人发言；不包含真实老师评价、雇主成效或公司数据。

Runtime source code was not changed while making these materials. The recording uses the source desktop interface; Windows EXE verification is documented separately in the current release.

制作材料未改变软件运行代码；录制画面使用源码桌面界面，EXE 的验证证据另见已有发布附件。

## Supplied files / 提供的文件

- `BatchScope-English-Demo.mp4`: final captioned video / 带字幕成片。
- `BatchScope-English-Narration.wav`: separate synthetic narration / 独立英文旁白。
- [English script](demo/ENGLISH_SCRIPT.md): replace with your own delivery when useful / 可用于练习或重配音。
- [English SRT](demo/ENGLISH_SUBTITLES.srt): timings estimated within each narrated chapter / 字幕时间按章节旁白分配。
- `VIDEO_MANIFEST.json` and `QUALITY_CHECK.json`: format, checksums, chapters and decode/audio checks / 格式、哈希、章节和音视频检查。
- [Simulated teacher review](teacher-review/REPORT.zh-CN.md) and [classroom worksheet](teacher-review/WORKSHEET.zh-CN.md).

The local delivery folder is `outputs/portfolio-demo-2026-10-01/delivery/`. Video/build intermediates remain outside Git source tracking. The captioned video and complete pack are published as assets of the release linked above.

本机成片位于上述 delivery 目录；视频与制作中间文件不进入源码跟踪。成片与完整材料包作为上方 Release 附件发布，不进入源码仓库。

## Technical notes / 制作核对

Local Windows speech synthesis produced WAV files. Pillow composed native screenshots with chapters/captions; the [imageio-ffmpeg project](https://github.com/imageio/imageio-ffmpeg) supplied a local FFmpeg executable. Encoding tools are installed only in an ignored build environment and are not application runtime dependencies.

Check the actual encoded video by full decoding, duration/stream inspection, audio-level analysis and representative frame inspection. The delivered version includes the resulting check record. The related teacher exercise checked 16 expectations across 11 task categories; it is not independent human usability research.
