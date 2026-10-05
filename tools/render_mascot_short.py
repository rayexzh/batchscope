"""Render a short, illustrated demo. Build-only: Pillow and imageio-ffmpeg.

This script is deliberately self-contained so each public repository can
rebuild its own video without depending on the other project.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import subprocess
import textwrap
import wave

from PIL import Image, ImageDraw, ImageFont
import imageio_ffmpeg


ROOT = Path(__file__).resolve().parents[1]
IS_RX = (ROOT / "src" / "rxdatalint").exists()
NAME = "RxDataLint" if IS_RX else "BatchScope"
REPO = "rx-data-lint" if IS_RX else "batchscope"
VERSION = "v0.4.0-alpha.4" if IS_RX else "v0.6.0-alpha.5"
ASSET = ROOT / "docs" / "demo" / "mascot"
OUT = ROOT / "outputs" / "mascot-short"
OUT.mkdir(parents=True, exist_ok=True)
W, H, FPS = 1280, 720, 16
CREAM, INK, TEAL, MINT, AMBER = "#f5f1e8", "#203b39", "#28786f", "#dbece1", "#d58b49"
FONTS = Path("C:/Windows/Fonts")


def font(size: int, *, bold: bool = False, chinese: bool = False) -> ImageFont.FreeTypeFont:
    filename = "msyh.ttc" if chinese else "segoeuib.ttf" if bold else "segoeui.ttf"
    return ImageFont.truetype(str(FONTS / filename), size)


TITLE, BODY, SMALL, ZH, CAPTION = font(49, bold=True), font(29), font(22), font(28, chinese=True), font(25, bold=True)

if IS_RX:
    SCENES = [
        ("A spreadsheet arrives", "先看数据，再看趋势", "Before analysing medicines data, check the file you downloaded.", "A medicine CSV arrives."),
        ("A flag asks a question", "负值可能是调整，先复核", "A negative value may be a stock adjustment. The flag asks for review, not a verdict.", "Negative does not always mean wrong."),
        ("Follow the source row", "按规则分组，回到原始记录", "Group findings by rule, organisation, or medicine. Then inspect the source row in the desktop app.", "Group findings. Inspect the row."),
        ("Keep the review trail", "导出完整报告，保留依据", "Export the findings before building local SQL summaries. Try the bundled sample to see the workflow.", "Review first. Analyse next."),
    ]
    mascot = Image.open(ASSET / "otter.png").convert("RGBA")
    screenshot = Image.open(ASSET / "checker-current.png").convert("RGB")
else:
    SCENES = [
        ("Follow a batch", "把批次与后续措施连起来", "A batch, its tests, a deviation, and follow-up actions belong in one review trail.", "One batch. Connected records."),
        ("Pause at a change", "修改原因空白，需要复核", "In this fictional audit log, a test value changes but the reason is blank. Look at the original event.", "A blank reason needs a closer look."),
        ("Open the evidence", "标记是线索，不是违规结论", "Search a flagged event, open its source row, and record your review. A flag is not a violation verdict.", "Inspect the event. Record the review."),
        ("Compare several dates", "沿时间线看状态变化", "Compare several as-of dates to see which actions became overdue or were resolved.", "See what changed, and when."),
        ("Try the synthetic example", "只用模拟数据，本地运行", "BatchScope uses synthetic records for this demonstration. Download the desktop app and try the included example.", "A local, synthetic quality demo."),
    ]
    mascot = Image.open(ASSET / "badger.png").convert("RGBA")
    screenshot = Image.open(ROOT / "docs" / "screenshots" / "audit-review-en.png").convert("RGB")


def t(d: ImageDraw.ImageDraw, xy: tuple[int, int], words: str, f=BODY, colour=INK):
    d.text(xy, words, font=f, fill=colour)


def card(d: ImageDraw.ImageDraw, box: tuple[int, int, int, int], label: str, detail: str = "", *, accent=TEAL):
    d.rounded_rectangle(box, radius=23, fill="#ffffff", outline="#c5d8cf", width=3)
    x, y, _, _ = box
    d.rounded_rectangle((x + 18, y + 21, x + 27, y + 85), radius=4, fill=accent)
    t(d, (x + 48, y + 22), label, CAPTION)
    if detail:
        t(d, (x + 48, y + 62), detail, SMALL, "#607a75")


def smooth(value: float) -> float:
    v = max(0.0, min(1.0, value))
    return v * v * (3 - 2 * v)


def mascot_on(im: Image.Image, seconds: float, x: int = 935, bottom: int = 600, height: int = 490):
    scale = height / mascot.height
    cutout = mascot.resize((round(mascot.width * scale), height), Image.Resampling.LANCZOS)
    # A small breathing motion keeps the character alive even during the screen capture.
    sway = round(math.sin(seconds * 2.7) * 5)
    bob = round(math.sin(seconds * 3.1) * 7)
    im.alpha_composite(cutout, (x + sway, bottom - height + bob))


def draw_scene(im: Image.Image, d: ImageDraw.ImageDraw, index: int, sec: float):
    rise = round((1 - smooth(sec / 0.8)) * 65)
    if IS_RX and index == 0:
        card(d, (93, 251 + rise, 392, 382 + rise), "SCMD CSV", "Synthetic sample")
        for n, (label, y) in enumerate((("Date", 260), ("Quantity", 365), ("Cost", 470))):
            x = 497 + round(math.sin(sec * 2 + n) * 9)
            card(d, (x, y, x + 310, y + 82), label, accent=AMBER if n == 1 else TEAL)
        d.line((394, 318, 485, 318), fill=TEAL, width=5)
        mascot_on(im, sec)
    elif IS_RX and index == 1:
        card(d, (105, 234, 787, 455), "Quantity: -18", "Possible stock adjustment", accent=AMBER)
        d.ellipse((602, 271, 693, 362), outline=AMBER, width=7)
        t(d, (632, 286), "?", TITLE, AMBER)
        card(d, (136, 476, 722, 568), "Review the source", accent=TEAL)
        mascot_on(im, sec)
    elif (IS_RX and index == 2) or (not IS_RX and index == 2):
        # Current native app capture, clearly framed as a capture rather than a drawn UI.
        shot = screenshot.copy()
        shot.thumbnail((835, 430), Image.Resampling.LANCZOS)
        x, y = 71, 200
        im.paste(shot, (x, y))
        d.rounded_rectangle((x - 5, y - 5, x + shot.width + 5, y + shot.height + 5), radius=10, outline=TEAL, width=4)
        mascot_on(im, sec, x=1009, bottom=603, height=348)
    elif IS_RX and index == 3:
        for n, (label, note) in enumerate((("Findings", "Review"), ("SQL", "Summarise"), ("Report", "Keep context"))):
            x = 75 + n * 280
            card(d, (x, 284 + rise, x + 249, 415 + rise), label, note)
            if n < 2:
                d.line((x + 254, 349 + rise, x + 272, 349 + rise), fill=TEAL, width=5)
        t(d, (86, 507), "github.com/rayexzh/rx-data-lint", BODY, TEAL)
        mascot_on(im, sec)
    elif not IS_RX and index == 0:
        card(d, (72, 310 + rise, 291, 446 + rise), "Batch", "B0001")
        for n, (label, note) in enumerate((("Test", "Result"), ("Deviation", "Case"), ("Action", "Follow-up"))):
            x = 353 + n * 182
            card(d, (x, 286 + rise, x + 166, 422 + rise), label, note)
            d.line((292 if n == 0 else x - 15, 378 + rise, x - 3, 378 + rise), fill=TEAL, width=4)
        mascot_on(im, sec, x=1016, height=410)
    elif not IS_RX and index == 1:
        card(d, (85, 237, 760, 501), "Event E002", "Synthetic audit event", accent=AMBER)
        t(d, (142, 341), "99  →  98", TITLE, TEAL)
        t(d, (142, 423), "Change reason: blank", BODY, "#ad6743")
        d.ellipse((609, 290, 702, 383), outline=AMBER, width=6)
        t(d, (638, 302), "?", TITLE, AMBER)
        mascot_on(im, sec)
    elif not IS_RX and index == 3:
        points = [(135, 488), (320, 450), (505, 428), (690, 393)]
        d.line((110, 515, 775, 515), fill="#92b3a5", width=4)
        progress = max(0, min(3, (sec - 0.5) * 0.7))
        for n in range(3):
            a, b = points[n], points[n + 1]
            frac = max(0, min(1, progress - n))
            if frac:
                d.line((*a, a[0] + (b[0] - a[0]) * frac, a[1] + (b[1] - a[1]) * frac), fill=TEAL, width=7)
        for n, (x, y) in enumerate(points):
            if progress >= n:
                d.ellipse((x - 10, y - 10, x + 10, y + 10), fill=AMBER)
            t(d, (x - 38, 538), ("Apr", "May", "Jun", "Jul")[n], SMALL)
        card(d, (106, 219, 763, 313), "Compare up to 12 dates", accent=TEAL)
        mascot_on(im, sec)
    else:
        card(d, (93, 262 + rise, 765, 407 + rise), "Synthetic records", "No company or patient data")
        t(d, (96, 500), "github.com/rayexzh/batchscope", BODY, TEAL)
        mascot_on(im, sec)


def frame(index: int, sec: float, total: int) -> Image.Image:
    im = Image.new("RGBA", (W, H), CREAM)
    d = ImageDraw.Draw(im)
    # Paper-like geometry is drawn in code; the character is the generated bitmap asset.
    d.ellipse((-120, 370, 370, 860), fill=MINT)
    d.ellipse((995, -260, 1510, 250), fill="#e3d9ca")
    d.rounded_rectangle((36, 28, 1244, 661), radius=36, outline="#c9d9cc", width=3)
    title, zh, _, _ = SCENES[index]
    t(d, (75, 54), NAME.upper() + "  /  SHORT EXPLAINER", SMALL, TEAL)
    t(d, (75, 94), title, TITLE)
    t(d, (77, 157), zh, ZH, "#57736a")
    draw_scene(im, d, index, sec)
    d.rectangle((0, 665, W, H), fill=INK)
    caption = SCENES[index][3]
    t(d, (55, 677), caption, CAPTION, "#ffffff")
    t(d, (941, 684), f"{index + 1} / {total}", SMALL, "#c5dbcf")
    d.rectangle((0, 660, round(W * (index + sec / 8) / total), 665), fill=TEAL)
    return im.convert("RGB")


def stamp(seconds: float) -> str:
    ms = round(seconds * 1000)
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


def make_audio():
    (OUT / "scenes.json").write_text(json.dumps([{"voice": s[2]} for s in SCENES]), encoding="utf-8-sig")
    ps = OUT / "voice.ps1"
    ps.write_text("""param([string]$Folder)
Add-Type -AssemblyName System.Speech
$ErrorActionPreference = 'Stop'
$speaker = New-Object System.Speech.Synthesis.SpeechSynthesizer
$speaker.SelectVoice('Microsoft Zira Desktop')
$speaker.Rate = 1
$scenes = Get-Content -LiteralPath (Join-Path $Folder 'scenes.json') -Raw -Encoding UTF8 | ConvertFrom-Json
for ($i = 0; $i -lt $scenes.Count; $i++) {
  $speaker.SetOutputToWaveFile((Join-Path $Folder ('voice-' + $i + '.wav')))
  $speaker.Speak($scenes[$i].voice)
  $speaker.SetOutputToNull()
}
$speaker.Dispose()
""", encoding="utf-8-sig")
    subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps), str(OUT)], check=True)
    blocks = []
    fmt = None
    for i in range(len(SCENES)):
        with wave.open(str(OUT / f"voice-{i}.wav")) as f:
            current = f.getparams()
            fmt = fmt or current
            assert (current.nchannels, current.sampwidth, current.framerate) == (fmt.nchannels, fmt.sampwidth, fmt.framerate)
            data = f.readframes(f.getnframes())
            assert f.getnframes() / f.getframerate() < 7.5, f"Narration exceeds scene {i}"
        unit = fmt.nchannels * fmt.sampwidth
        block = bytes(round(0.25 * fmt.framerate) * unit) + data
        length = round(8 * fmt.framerate) * unit
        blocks.append(block + bytes(length - len(block)))
    audio = OUT / f"{NAME}-Mascot-Voice.wav"
    with wave.open(str(audio), "wb") as f:
        f.setnchannels(fmt.nchannels)
        f.setsampwidth(fmt.sampwidth)
        f.setframerate(fmt.framerate)
        f.writeframes(b"".join(blocks))
    return audio


def main():
    audio = make_audio()
    duration = len(SCENES) * 8
    subtitles = "\n\n".join(f"{i + 1}\n{stamp(i * 8)} --> {stamp((i + 1) * 8)}\n" + "\n".join(textwrap.wrap(s[2], 72)) for i, s in enumerate(SCENES)) + "\n"
    (OUT / f"{NAME}-Mascot-English.srt").write_text(subtitles, encoding="utf-8")
    chinese = "\n\n".join(f"{i + 1}\n{stamp(i * 8)} --> {stamp((i + 1) * 8)}\n{s[1]}" for i, s in enumerate(SCENES)) + "\n"
    (OUT / f"{NAME}-Mascot-Chinese.srt").write_text(chinese, encoding="utf-8")
    poster = ASSET / "poster.png"
    frame(0, 2.0, len(SCENES)).save(poster, optimize=True)
    video = OUT / f"{NAME}-Mascot-Short-{VERSION}.mp4"
    command = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-i", str(audio), "-c:v", "libx264", "-preset", "veryfast", "-crf", "24", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "112k", "-t", str(duration), "-movflags", "+faststart", str(video)]
    with subprocess.Popen(command, stdin=subprocess.PIPE) as proc:
        assert proc.stdin is not None
        for n in range(duration * FPS):
            scene, local = divmod(n, 8 * FPS)
            im = frame(scene, local / FPS, len(SCENES))
            proc.stdin.write(im.tobytes())
            if n % (FPS * 8) == 0:
                print(f"{NAME}: rendered scene {scene + 1}/{len(SCENES)}", flush=True)
        proc.stdin.close()
        assert proc.wait() == 0, "ffmpeg encoding failed"
    digest = hashlib.sha256(video.read_bytes()).hexdigest()
    (OUT / "checks.json").write_text(json.dumps({"project": NAME, "version": VERSION, "duration_seconds": duration, "resolution": [W, H], "fps": FPS, "video_sha256": digest, "video_bytes": video.stat().st_size}, indent=2), encoding="utf-8")
    print(f"Video: {video}\nSHA256: {digest}\nPoster: {poster}")


if __name__ == "__main__":
    main()
