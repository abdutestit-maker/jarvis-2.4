#!/usr/bin/env python
"""Create the compact transparent Signal Core application icon."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "jarvis" / "src-tauri" / "icons"


def render(size: int) -> Image.Image:
    scale = 4
    canvas = size * scale
    image = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    center = canvas // 2
    radius = int(canvas * 0.35)
    # Matte graphite core with a thin cyan activation ring.
    draw.ellipse((center - radius, center - radius, center + radius, center + radius),
                 fill=(7, 10, 14, 244), outline=(30, 47, 58, 255), width=max(2, scale * 2))
    ring = int(canvas * 0.42)
    draw.arc((center - ring, center - ring, center + ring, center + ring),
             start=202, end=338, fill=(0, 207, 232, 230), width=max(2, scale * 3))
    # Signal bars are the single brand element used by the frontend presence core.
    bar_width = max(2, int(canvas * 0.035))
    gap = max(2, int(canvas * 0.022))
    heights = [0.22, 0.42, 0.66, 0.42, 0.22]
    total = len(heights) * bar_width + (len(heights) - 1) * gap
    left = center - total // 2
    for index, ratio in enumerate(heights):
        x0 = left + index * (bar_width + gap)
        half = int(canvas * ratio * 0.18)
        draw.rounded_rectangle((x0, center - half, x0 + bar_width, center + half),
                               radius=max(1, bar_width // 2), fill=(0, 219, 239, 255))
    image = image.resize((size, size), Image.Resampling.LANCZOS)
    return image


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for size, name in ((256, "256x256.png"), (512, "128x128@2x.png"),
                       (128, "128x128.png"), (32, "32x32.png")):
        render(size).save(OUT / name, "PNG", optimize=True)
    render(256).save(OUT / "icon.ico", "ICO", sizes=[(256, 256), (128, 128), (32, 32), (16, 16)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
