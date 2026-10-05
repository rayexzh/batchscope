# Badger short / 小獾短片

The 40-second MP4 was rendered for BatchScope v0.6.0-alpha.5. All batch and audit records are synthetic. The audit scene includes a current native desktop capture. The badger is an AI-generated illustration; moving record cards explain the workflow. Microsoft Zira Desktop synthesised the English voice. This is not a real user endorsement or a regulatory validation. / 40 秒短片仅用模拟数据与当前软件截图。小獾是生成插画，英文旁白由本机合成；不代表真实用户评价或监管验证。

[Video](BatchScope-Mascot-Short-v0.6.0-alpha.5.mp4) · [English subtitles](English.srt) · [Chinese highlights](Chinese.srt) · [Poster](poster.png)

To rebuild on Windows, use a separate build environment with Pillow and imageio-ffmpeg, then run `python tools/render_mascot_short.py` from the repository root. These packages are needed only for media rendering; BatchScope itself uses the standard library. The source image prompt asked for a calm European badger with a navy work jacket and clipboard, a soft picture-book style, and a transparent background. The exported MP4 is H.264/AAC, 1280×720, 16 fps. / Windows 构建环境需 Pillow、imageio-ffmpeg；软件本身不需要这些依赖。
