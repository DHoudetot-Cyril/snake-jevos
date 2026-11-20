# /// script
# requires-python = ">=3.10"
# dependencies = ["playwright>=1.50", "pillow>=10"]
# ///
"""Filme une vraie partie jouée par jevos et en fait docs/demo.gif.

Le jeu doit tourner (./start.sh). Un Chromium sans interface ouvre la page, active jevos, puis
prend des captures d'écran en rafale pendant DURÉE secondes. Les captures sont sans perte, et
chaque image du GIF garde sa durée réelle : la partie est montrée en temps réel.

    uv run tools/record_demo.py                     # 28 s, 900 px de large, 10 images/s
    uv run tools/record_demo.py --chrome /chemin/vers/chrome --duration 20

Sans --chrome, il faut un navigateur Playwright : `uvx playwright install chromium`.
Outil de développement uniquement : le jeu, lui, reste en bibliothèque standard.
"""

from __future__ import annotations

import argparse
import asyncio
import tempfile
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from playwright.async_api import async_playwright

ROOT = Path(__file__).resolve().parents[1]
CAPTION = "Vraie partie, en temps réel : jevos-v5 sur CPU joue seul (8 questions oui/non par coup, ~50 ms)"


async def capture(url: str, chrome: str | None, seconds: float, folder: Path) -> tuple[list[float], dict]:
    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=chrome)
        page = await browser.new_page(viewport={"width": 1280, "height": 800})
        await page.goto(url)
        await page.wait_for_timeout(1500)
        await page.click("#btnAi")
        stamps: list[float] = []
        t0 = time.monotonic()
        while time.monotonic() - t0 < seconds:
            t = time.monotonic() - t0
            await page.screenshot(path=folder / f"{len(stamps):05d}.png")
            stamps.append(t)
        stats = {k: await page.inner_text(f"#{k}") for k in ("sScore", "sDec", "sLat", "sDead")}
        await browser.close()
    return stamps, stats


def assemble(folder: Path, stamps: list[float], out: Path, width: int, fps: float) -> None:
    # une image par 1/fps seconde de temps réel (la capture la plus proche)
    picks: list[int] = []
    t, i = 0.0, 0
    while t <= stamps[-1]:
        while i + 1 < len(stamps) and abs(stamps[i + 1] - t) <= abs(stamps[i] - t):
            i += 1
        if not picks or picks[-1] != i:
            picks.append(i)
        t += 1 / fps
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 13)
    except OSError:
        font = ImageFont.load_default()
    frames = []
    for k in picks:
        im = Image.open(folder / f"{k:05d}.png").convert("RGB")
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
        canvas = Image.new("RGB", (im.width, im.height + 26), (15, 17, 21))
        canvas.paste(im, (0, 0))
        ImageDraw.Draw(canvas).text((12, im.height + 6), CAPTION, font=font, fill=(140, 140, 150))
        frames.append(canvas)
    durations = [round((stamps[b] - stamps[a]) * 1000) for a, b in zip(picks, picks[1:])] + [2500]

    # Palette commune ; les couleurs rares mais importantes (la pomme) reçoivent une pastille.
    sample = Image.new("RGB", (frames[0].width, frames[0].height * 3 + 120), (0, 0, 0))
    for n, f in enumerate((frames[0], frames[len(frames) // 2], frames[-1])):
        sample.paste(f, (0, n * f.height))
    raw = Image.open(folder / f"{picks[len(picks) // 2]:05d}.png").convert("RGB")
    reds = [px for px in raw.getdata() if px[0] > 200 and px[1] < 140 and px[2] < 140]
    if reds:
        apple = tuple(sum(c) // len(reds) for c in zip(*reds))
        sample.paste(Image.new("RGB", (sample.width, 120), apple), (0, frames[0].height * 3))
    palette = sample.quantize(colors=220, method=Image.Quantize.MEDIANCUT)
    quantized = [f.quantize(palette=palette, dither=Image.Dither.NONE) for f in frames]
    quantized[0].save(
        out, save_all=True, append_images=quantized[1:], duration=durations, loop=0, optimize=True
    )
    print(f"{out} : {len(quantized)} images, {sum(durations) / 1000:.0f} s, {out.stat().st_size / 1e6:.1f} Mo")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--url", default="http://127.0.0.1:8080")
    parser.add_argument("--chrome", help="exécutable Chromium (sinon celui de Playwright)")
    parser.add_argument("--duration", type=float, default=28)
    parser.add_argument("--width", type=int, default=900)
    parser.add_argument("--fps", type=float, default=10)
    parser.add_argument("-o", "--output", type=Path, default=ROOT / "docs" / "demo.gif")
    args = parser.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        stamps, stats = asyncio.run(capture(args.url, args.chrome, args.duration, folder))
        print(f"{len(stamps)} captures · score {stats['sScore']} · {stats['sDec']} décisions · "
              f"latence moy. {stats['sLat']} · choix mortels {stats['sDead']}")
        assemble(folder, stamps, args.output, args.width, args.fps)


if __name__ == "__main__":
    main()
