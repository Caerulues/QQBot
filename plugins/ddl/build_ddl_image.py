from datetime import datetime

from PIL import Image, ImageDraw
import io
import textwrap

from utils.font import load_font

# MARK: 图片生成

def build_ddl_image(data):
    width = 1000
    padding = 40
    row_h = 70

    base_font_size = 32

    if len(data) > 10:
        base_font_size = 24

    if len(data) > 20:
        base_font_size = 16

    font = load_font(base_font_size)

    height = padding * 2 + 80 + len(data) * row_h

    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)

    y = padding

    # 表头
    draw.text((padding + 10, y + 8), "UUID", font=font, fill=(0, 0, 0))
    draw.text((padding + 200, y + 8), "TITLE", font=font, fill=(0, 0, 0))
    draw.text((padding + 550, y + 8), "DEADLINE", font=font, fill=(0, 0, 0))
    draw.text((padding + 800, y + 8), "REMAIN", font=font, fill=(0, 0, 0))

    y += 50

    for item in data:
        remain = int(item["time"] - datetime.now().timestamp())

        if remain < 0:
            color = (255, 80, 80)

        elif remain < 86400:
            color = (255, 180, 0)

        else:
            color = (0, 0, 0)

        if remain < 0:
            remain_text = "EXPIRED"

        else:
            days = remain // 86400
            hours = (remain % 86400) // 3600
            minutes = (remain % 3600) // 60

            if days > 0:
                remain_text = f"{days}d {hours}h"

            else:
                remain_text = f"{hours}h {minutes}m"

        dt = datetime.fromtimestamp(
            item["time"]
        ).strftime("%m-%d %H:%M")

        draw.text(
            (padding + 10, y),
            item["id"],
            font=font,
            fill=color
        )

        title_lines = textwrap.wrap(
            item["title"],
            width=12
        )

        for i, line in enumerate(title_lines[:2]):
            draw.text(
                (padding + 200, y + i * 26),
                line,
                font=font,
                fill=color
            )

        draw.text(
            (padding + 550, y),
            dt,
            font=font,
            fill=color
        )

        draw.text(
            (padding + 800, y),
            remain_text,
            font=font,
            fill=color
        )

        y += row_h

    buf = io.BytesIO()
    img.save(buf, format="PNG")

    return buf.getvalue()