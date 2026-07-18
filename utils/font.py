import platform
from PIL import ImageFont
from pathlib import Path
from config import config

PROJECT_FONT = Path(config.data_dir) / "fonts" / "NotoSansSC-Regular.ttf"

def get_font_candidates() -> list[Path]:
    system = platform.system()

    if system == "Darwin":  # macOS
        return [
            Path("/System/Library/Fonts/PingFang.ttc"),
            Path("/System/Library/Fonts/Hiragino Sans GB.ttc"),
            Path("/System/Library/Fonts/Supplemental/Songti.ttc"),
            PROJECT_FONT,
        ]

    if system == "Windows":
        return [
            Path("C:/Windows/Fonts/msyh.ttc"),   # 微软雅黑
            Path("C:/Windows/Fonts/simhei.ttf"), # 黑体
            Path("C:/Windows/Fonts/Deng.ttf"),   # 等线
            PROJECT_FONT,
        ]

    return [  # Linux
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
        PROJECT_FONT,
    ]


def load_font(size: int):
    for path in get_font_candidates():
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size)
            except OSError:
                continue

    return ImageFont.load_default()