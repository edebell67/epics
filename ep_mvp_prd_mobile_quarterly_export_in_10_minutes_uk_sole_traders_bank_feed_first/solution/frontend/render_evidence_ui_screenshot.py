from __future__ import annotations

import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


WIDTH = 390
HEIGHT = 844


def load_font(size: int, bold: bool = False, serif: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    candidates = []
    if serif:
      candidates.extend([
          "C:/Windows/Fonts/georgia.ttf",
          "C:/Windows/Fonts/times.ttf",
      ])
    elif bold:
      candidates.extend([
          "C:/Windows/Fonts/arialbd.ttf",
          "C:/Windows/Fonts/segoeuib.ttf",
      ])
    else:
      candidates.extend([
          "C:/Windows/Fonts/arial.ttf",
          "C:/Windows/Fonts/segoeui.ttf",
      ])

    for candidate in candidates:
        if Path(candidate).exists():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def text(draw: ImageDraw.ImageDraw, xy: tuple[int, int], value: str, font, fill, anchor=None):
    draw.text(xy, value, font=font, fill=fill, anchor=anchor)


def rounded(draw: ImageDraw.ImageDraw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def wrap(value: str, max_chars: int) -> list[str]:
    words = value.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = word if not current else f"{current} {word}"
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render(payload_path: Path, output_path: Path) -> None:
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    image = Image.new("RGB", (WIDTH, HEIGHT), "#f2dfc7")
    draw = ImageDraw.Draw(image)

    heading_font = load_font(34, serif=True)
    body_font = load_font(14)
    label_font = load_font(11, bold=True)
    title_font = load_font(18, bold=True)
    amount_font = load_font(16, bold=True)
    chip_font = load_font(11)
    small_font = load_font(12)

    draw.ellipse((20, 0, 220, 200), fill="#efd5bd")
    draw.ellipse((250, 560, 430, 780), fill="#e6c6aa")

    rounded(draw, (18, 18, WIDTH - 18, HEIGHT - 18), 38, "#fff9f0", outline="#f3e4d5")

    text(draw, (38, 48), "EVIDENCE ATTACH", label_font, "#9e3113")
    for index, line in enumerate(wrap("Match the receipt before the export queue moves on.", 24)):
        text(draw, (38, 74 + (index * 34)), line, heading_font, "#25160f")

    hero_lines = wrap(payload["heroCopy"], 42)
    for index, line in enumerate(hero_lines):
        text(draw, (38, 176 + (index * 19)), line, body_font, "#6c5b4e")

    contexts = payload["contexts"]
    context_y = 248
    for index, context in enumerate(contexts):
        box_top = context_y + index * 60
        fill = "#f7d9cb" if context["id"] == "quarter-close" else "#fff6ee"
        rounded(draw, (30, box_top, WIDTH - 30, box_top + 48), 16, fill, outline="#e6c8b6")
        text(draw, (44, box_top + 12), context["label"], body_font, "#25160f")
        text(draw, (44, box_top + 28), context["summary"], small_font, "#6c5b4e")

    rounded(draw, (30, 380, WIDTH - 30, 564), 24, "#fff7ef", outline="#eedccd")
    text(draw, (48, 402), "RECEIPT CAPTURE", label_font, "#9e3113")
    text(draw, (48, 426), payload["evidence"]["fileName"], title_font, "#25160f")
    preview_box = (48, 462, 124, 556)
    rounded(draw, preview_box, 18, "#f0ddd0")
    for y in range(474, 548, 12):
        draw.line((58, y, 112, y), fill="#ccb39f", width=1)

    evidence = payload["evidence"]
    text(draw, (144, 466), f"Merchant  {evidence['merchant']}", body_font, "#25160f")
    text(draw, (144, 492), f"Date        {evidence['doc_date']}", body_font, "#25160f")
    text(draw, (144, 518), f"Amount    GBP {evidence['amount']:.2f}", body_font, "#25160f")

    rounded(draw, (48, 580, WIDTH - 48, 648), 24, "#fff7ef", outline="#eedccd")
    text(draw, (64, 598), "CURRENT STATUS", label_font, "#9e3113")
    text(draw, (64, 620), "No export blockers created", title_font, "#155c3c")

    sheet_top = 448
    rounded(draw, (16, sheet_top, WIDTH - 16, HEIGHT - 16), 28, "#221710")
    rounded(draw, (170, sheet_top + 10, 220, sheet_top + 16), 3, "#66594f")
    text(draw, (34, sheet_top + 30), "TOP 3 CANDIDATES", label_font, "#ffb597")
    text(draw, (34, sheet_top + 54), "Confirm the best bank match", title_font, "#fff5e9")

    candidate_top = sheet_top + 100
    for index, candidate in enumerate(payload["candidates"]):
        top = candidate_top + index * 100
        fill = "#4d291e" if candidate["candidate_rank"] == 1 else "#30251f"
        outline = "#ce5e36" if candidate["candidate_rank"] == 1 else "#4d3b33"
        rounded(draw, (28, top, WIDTH - 28, top + 88), 20, fill, outline=outline)
        lead = "BEST MATCH" if candidate["candidate_rank"] == 1 else f"CHOICE {candidate['candidate_rank']}"
        text(draw, (42, top + 12), lead, label_font, "#ffb597")
        text(draw, (WIDTH - 44, top + 12), f"{int(candidate['link_confidence'] * 100)}%", label_font, "#ffe2d2", anchor="ra")
        text(draw, (42, top + 32), candidate["merchant"], body_font, "#fff5e9")
        text(draw, (WIDTH - 44, top + 32), f"GBP {candidate['amount']:.2f}", amount_font, "#fff5e9", anchor="ra")
        text(draw, (42, top + 52), candidate["date"], small_font, "#d7c3b5")
        chip_x = 42
        chip_y = top + 64
        for reason in candidate["reasons"]:
            chip_width = max(56, 8 * len(reason))
            rounded(draw, (chip_x, chip_y, chip_x + chip_width, chip_y + 18), 9, "#3b3028")
            text(draw, (chip_x + 8, chip_y + 3), reason, chip_font, "#ffe1cf")
            chip_x += chip_width + 6

    footer_top = HEIGHT - 116
    rounded(draw, (28, footer_top, WIDTH - 28, footer_top + 18), 9, "#ce5e36")
    text(draw, (WIDTH // 2, footer_top + 2), "Confirm match", body_font, "#fff9f2", anchor="ma")
    rounded(draw, (28, footer_top + 28, WIDTH - 28, footer_top + 46), 9, "#3c3129", outline="#514037")
    text(draw, (WIDTH // 2, footer_top + 30), "No match", body_font, "#fff0e1", anchor="ma")
    rounded(draw, (28, footer_top + 56, WIDTH - 28, footer_top + 74), 9, "#271d18", outline="#45362d")
    text(draw, (WIDTH // 2, footer_top + 58), "Later", body_font, "#d8c0af", anchor="ma")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python render_evidence_ui_screenshot.py <payloadPath> <outputPath>")
    render(Path(sys.argv[1]), Path(sys.argv[2]))
