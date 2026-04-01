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

    heading_font = load_font(31, serif=True)
    body_font = load_font(14)
    label_font = load_font(11, bold=True)
    title_font = load_font(18, bold=True)
    amount_font = load_font(16, bold=True)
    chip_font = load_font(11)
    small_font = load_font(12)

    draw.ellipse((10, -10, 220, 200), fill="#efd5bd")
    draw.ellipse((230, 570, 420, 790), fill="#e6c6aa")

    rounded(draw, (18, 18, WIDTH - 18, HEIGHT - 18), 38, "#fff9f0", outline="#f3e4d5")
    rounded(draw, (28, 32, WIDTH - 28, 90), 28, "#eff7f1", outline="#d7e7db")
    text(draw, (46, 47), "APPLIED BY VOICE", label_font, "#155c3c")
    text(draw, (46, 66), "Category set to Travel", title_font, "#1f160f")
    rounded(draw, (290, 46, WIDTH - 42, 78), 16, "#155c3c")
    text(draw, (339, 53), "Undo", body_font, "#fff9f2", anchor="ma")

    text(draw, (38, 118), "VOICE TRIAGE", label_font, "#9e3113")
    for index, line in enumerate(wrap("Speak or tap once. Confirm what changed. Undo in one tap.", 26)):
        text(draw, (38, 144 + (index * 32)), line, heading_font, "#25160f")

    for index, line in enumerate(wrap(payload["heroCopy"], 42)):
        text(draw, (38, 242 + (index * 18)), line, body_font, "#6c5b4e")

    rounded(draw, (30, 316, WIDTH - 30, 448), 24, "#fff7ef", outline="#eedccd")
    text(draw, (48, 336), "INBOX MICRO-DECISION", label_font, "#9e3113")
    text(draw, (48, 362), payload["transaction"]["merchant"], title_font, "#25160f")
    text(draw, (48, 388), f"Amount  GBP {payload['transaction']['amount']:.2f}", body_font, "#25160f")
    text(draw, (48, 412), "Category  Travel", body_font, "#25160f")
    text(draw, (48, 432), "Business or personal  Missing", body_font, "#6c5b4e")

    button_labels = ["Category: Travel", "Business", "Personal", "Split 40%", "Attach receipt", "No match"]
    button_y = 466
    x_positions = [30, 170]
    for index, label in enumerate(button_labels):
        row = index // 2
        col = index % 2
        left = x_positions[col]
        top = button_y + row * 48
        rounded(draw, (left, top, left + 140, top + 34), 17, "#fffefe", outline="#e1c7b7")
        text(draw, (left + 12, top + 9), label, small_font, "#25160f")

    sheet_top = 618
    rounded(draw, (16, sheet_top, WIDTH - 16, HEIGHT - 16), 28, "#221710")
    rounded(draw, (170, sheet_top + 10, 220, sheet_top + 16), 3, "#66594f")
    text(draw, (34, sheet_top + 28), "TOP 3 CANDIDATES", label_font, "#ffb597")
    text(draw, (34, sheet_top + 52), "Confirm the best bank match", title_font, "#fff5e9")

    candidate = payload["candidates"][0]
    rounded(draw, (28, sheet_top + 86, WIDTH - 28, sheet_top + 174), 20, "#4d291e", outline="#ce5e36")
    text(draw, (42, sheet_top + 100), "BEST MATCH", label_font, "#ffb597")
    text(draw, (WIDTH - 44, sheet_top + 100), f"{int(candidate['link_confidence'] * 100)}%", label_font, "#ffe2d2", anchor="ra")
    text(draw, (42, sheet_top + 120), candidate["merchant"], body_font, "#fff5e9")
    text(draw, (WIDTH - 44, sheet_top + 120), f"GBP {candidate['amount']:.2f}", amount_font, "#fff5e9", anchor="ra")
    text(draw, (42, sheet_top + 140), candidate["date"], small_font, "#d7c3b5")

    chip_x = 42
    for reason in candidate["reasons"]:
        chip_width = max(58, 8 * len(reason))
        rounded(draw, (chip_x, sheet_top + 150, chip_x + chip_width, sheet_top + 168), 9, "#3b3028")
        text(draw, (chip_x + 8, sheet_top + 153), reason, chip_font, "#ffe1cf")
        chip_x += chip_width + 6

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python render_voice_ui_screenshot.py <payloadPath> <outputPath>")
    render(Path(sys.argv[1]), Path(sys.argv[2]))
