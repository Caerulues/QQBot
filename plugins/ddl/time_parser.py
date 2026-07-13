import jionlp as jio
from datetime import datetime

# MARK: 时间处理

def parse_ddl_line(text: str):
    try:
        parts = text.rsplit(" ", 1)

        if len(parts) != 2:
            return None

        title = parts[0].strip()
        time_str = parts[1].strip()

        result = jio.parse_time(
            time_str,
            time_base=datetime.now()
        )

        if not result:
            return None

        start_time = result["time"][0]

        if isinstance(start_time, datetime):
            ddl_time = start_time

        else:
            ddl_time = datetime.strptime(
                start_time,
                "%Y-%m-%d %H:%M:%S"
            )

        return {
            "title": title,
            "time": ddl_time
        }

    except Exception as e:
        print(f"[Parse Error] {e}")
        return None
