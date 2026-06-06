import re
import dateparser
import jionlp as jio
from datetime import datetime

DATE_PATTERNS = [
    # YYYY-MM-DD / YYYY/MM/DD
    r"[1-9]\d{3}[-/](?:0?[1-9]|1[0-2])[-/](?:[0-2]?\d|3[01])",

    # YYYY年MM月DD日 / MM月DD日
    r"(?:[1-9]\d{3}年)?(?:0?[1-9]|1[0-2])月(?:[0-2]?\d|3[01])(?:日|号)",

    # 中文数字年月日（简化版）
    r"[零一二三四五六七八九十]{2,4}年[零一二三四五六七八九十]+月[零一二三四五六七八九十]+(?:日|号)",
]

RELATIVE_DAY_PATTERNS = [
    r"(今天|明天|后天|大后天|前天|大前天|昨日|今日|前日|前一天)",

    r"(今|明|后)\s*天",

    r"(本|这|下|上)\s*(周|星期|礼拜)\s*[一二三四五六日天]?",
]

RELATIVE_CALENDAR_PATTERNS = [
    r"(上个|上上|下个|下下|这个|这|本|上|下)\s*月",

    r"(上个|上上|下个|下下|这个|这|本|上|下)?\s*(星期|周|礼拜)\s*[一二三四五六日天]",
]

TIME_OF_DAY_PATTERNS = [
    # 早上/下午 + 14:30
    r"(早上|上午|中午|下午|晚上|凌晨)\s*\d{1,2}(:\d{1,2}){0,2}",

    # 14:30 / 14:30:20
    r"\b(?:[01]?\d|2[0-3]):[0-5]?\d(?::[0-5]?\d)?\b",

    # 3点 / 3点20分 / 3时20分
    r"(?:[0-1]?\d|2[0-3])\s*(点|时)(\s*[0-5]?\d\s*分)?(\s*[0-5]?\d\s*秒)?",
]

CN_TIME_PATTERNS = [
    r"(早上|上午|中午|下午|晚上)\s*(十|十一|十二|[一二三四五六七八九]|\d{1,2})\s*(点|时)",

    r"(十|半|一刻|三刻|\d+)\s*(分钟|分)\s*(前|后)?",

    r"(半个|一个)?小时\s*(前|后)?",
]

RELATIVE_DURATION_PATTERNS = [
    # 5分钟后 / 一小时后 / 半小时后
    r"(\d+|半|一|二|三|四|五|六|七|八|九|十|几)?\s*(秒|分钟|分|小时|天|日|周|星期|个月|月|年)\s*(前|后|之?后|之?前)",

    # 10分钟内
    r"(\d+|半|一|几)?\s*(分钟|分|小时|天|日)\s*内",

    # 一刻 / 半小时 / 一小时后
    r"(一刻|半小时|一个小时|半个小时)\s*(前|后)?",
]

SINGLE_TIME_PATTERNS = [
    r"(?:早上|上午|中午|下午|晚上)?\s*(十|十一|十二|[一二三四五六七八九]|[0-9]|1[0-9]|2[0-3])\s*(点|时)\s*(\d{1,2}\s*分)?",
]

TIME_PATTERNS = (
    DATE_PATTERNS +
    RELATIVE_DAY_PATTERNS +
    RELATIVE_CALENDAR_PATTERNS +
    TIME_OF_DAY_PATTERNS +
    CN_TIME_PATTERNS +
    RELATIVE_DURATION_PATTERNS+
    SINGLE_TIME_PATTERNS
)

pattern = re.compile("|".join(TIME_PATTERNS))

def extract_time_segment(text: str):
    for p in TIME_PATTERNS:
        m = re.search(p, text)
        if m:
            return m.group()
    return None

def parse_time(text: str):
    text = text.strip()

    jio_result = jio.parse_time(text)
    if jio_result and jio_result.get("time"):
        dt = jio_result["time"][1]
        if hasattr(dt, "timestamp"):
            return dt.timestamp()

    for p in TIME_PATTERNS:
        m = re.search(p, text)
        if m:
            dt = dateparser.parse(m.group(), languages=["zh"])
            if isinstance(dt, datetime):
                return dt.timestamp()

    seg = extract_time_segment(text)
    if seg:
        dt = dateparser.parse(seg, languages=["zh"])

    return None

def parse_ddl_line(text: str):
    text = text.strip()

    parts = text.split(" ", 1)

    if len(parts) == 1:
        return None

    name, time_text = parts[0], parts[1]

    ts = parse_time(time_text)

    if not ts:
        return None

    return {
        "title": name,
        "time": ts
    }