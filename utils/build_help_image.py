import io
from PIL import Image, ImageDraw
from utils.font import load_font


def split_line(line: str) -> tuple[str, str]:
    if " - " in line:
        left, right = line.split(" - ", 1)
        return left.strip(), right.strip()

    return line.strip(), ""

def wrap_text(text: str, font, max_width: int) -> list[str]:
    if not text:
        return [""]

    lines = []
    current = ""

    for char in text:
        test = current + char
        bbox = font.getbbox(test)
        width = bbox[2] - bbox[0]

        if width <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = char

    if current:
        lines.append(current)

    return lines

def render_image(lines: list[str]) -> bytes:
    title_font = load_font(34)
    section_font = load_font(30)
    cmd_font = load_font(25)
    desc_font = load_font(24)

    padding = 36
    width = 1100
    content_width = width - padding * 2
    row_padding = 18
    line_gap = 8
    block_gap = 14

    rows = []

    for line in lines:
        if line == "":
            rows.append(("blank", "", "", 18))
            continue

        left, right = split_line(line)

        if right == "":
            rows.append(("section", left, "", 54))
        else:
            cmd_lines = wrap_text(left, cmd_font, content_width - row_padding * 2)
            desc_lines = wrap_text(right, desc_font, content_width - row_padding * 2)

            cmd_h = len(cmd_lines) * 30 + max(0, len(cmd_lines) - 1) * line_gap
            desc_h = len(desc_lines) * 28 + max(0, len(desc_lines) - 1) * line_gap

            height = row_padding * 2 + cmd_h + 8 + desc_h
            rows.append(("row", cmd_lines, desc_lines, height))

    height = padding * 2 + sum(row[3] for row in rows) + block_gap * len(rows)

    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    y = padding

    for row in rows:
        row_type = row[0]
        row_height = row[3]

        if row_type == "blank":
            y += row_height
            continue

        if row_type == "section":
            draw.rectangle(
                [padding, y, width - padding, y + row_height],
                fill=(235, 235, 235),
                outline=(180, 180, 180)
            )
            draw.text(
                (padding + row_padding, y + 10),
                row[1],
                font=section_font,
                fill=(20, 20, 20)
            )
            y += row_height + block_gap
            continue

        cmd_lines = row[1]
        desc_lines = row[2]

        draw.rectangle(
            [padding, y, width - padding, y + row_height],
            fill=(255, 255, 255),
            outline=(200, 200, 200)
        )

        text_y = y + row_padding

        for text in cmd_lines:
            draw.text(
                (padding + row_padding, text_y),
                text,
                font=cmd_font,
                fill=(20, 20, 20)
            )
            text_y += 30 + line_gap

        text_y += 4

        for text in desc_lines:
            draw.text(
                (padding + row_padding, text_y),
                text,
                font=desc_font,
                fill=(70, 70, 70)
            )
            text_y += 28 + line_gap

        y += row_height + block_gap

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()