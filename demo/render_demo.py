#!/usr/bin/env python3
"""Render the Sloth demo video from real captured output.

Usage: render_demo.py <screens.json> <out.mp4>
screens.json: [{"title": str, "body": str, "duration": seconds, "accent": bool}]
Renders 1280x720 PNGs with DejaVu Sans Mono, then ffmpeg -> mp4.
"""
import json
import os
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFont

W, H = 1280, 720
BG = (18, 22, 28)
FG = (220, 228, 238)
DIM = (130, 140, 155)
GREEN = (120, 220, 150)
YELLOW = (240, 200, 110)
ACCENT_BG = (24, 34, 40)

FONT_PATH = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"
TITLE_FONT = ImageFont.truetype(FONT_PATH, 40)
BODY_FONT = ImageFont.truetype(FONT_PATH, 24)
SMALL_FONT = ImageFont.truetype(FONT_PATH, 20)


def wrap(draw, text, font, max_w):
    lines = []
    for para in text.split("\n"):
        if not para.strip():
            lines.append("")
            continue
        words, cur = para.split(), ""
        for w in words:
            trial = (cur + " " + w).strip()
            if draw.textlength(trial, font=font) <= max_w:
                cur = trial
            else:
                lines.append(cur)
                cur = w
        lines.append(cur)
    return lines


def render_screen(title, body, accent, path):
    img = Image.new("RGB", (W, H), ACCENT_BG if accent else BG)
    d = ImageDraw.Draw(img)
    y = 60
    if title:
        d.text((70, y), title, font=TITLE_FONT, fill=GREEN if accent else YELLOW)
        y += 70
        d.line([(70, y), (W - 70, y)], fill=(60, 70, 85), width=2)
        y += 30
    for line in wrap(d, body, BODY_FONT, W - 160):
        if y > H - 60:
            break
        d.text((80, y), line, font=BODY_FONT, fill=FG)
        y += 34
    d.text((W - 300, H - 44), "github.com/raju12345-raju/sloth",
           font=SMALL_FONT, fill=DIM)
    img.save(path)


def main():
    screens_path, out_mp4 = sys.argv[1], sys.argv[2]
    screens = json.load(open(screens_path))
    tmp = tempfile.mkdtemp(prefix="slothdemo")
    inputs, filt = [], []
    for i, s in enumerate(screens):
        png = os.path.join(tmp, f"screen{i:02d}.png")
        render_screen(s.get("title", ""), s.get("body", ""),
                      s.get("accent", False), png)
        inputs += ["-loop", "1", "-t", str(s.get("duration", 5)), "-i", png]
    n = len(screens)
    # concat
    fc = "".join(f"[{i}:v]" for i in range(n)) + f"concat=n={n}:v=1:a=0[v]"
    cmd = (["ffmpeg", "-y"] + inputs +
           ["-filter_complex", fc, "-map", "[v]", "-r", "30",
            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "22", out_mp4])
    subprocess.run(cmd, check=True, capture_output=True)
    print("wrote", out_mp4,
          f"({sum(s.get('duration', 5) for s in screens)}s)")


main()
