# MARK: 提醒规则（动态）

REMIND_STAGES = [
    (0, "remind_now", "now"),
    (3600, "reminded_1h", "1h"),
    (86400, "reminded_1d", "1d"),
    (7 * 86400, "reminded_1w", "1w"),
]

def should_remind(item, remain):
    if remain <= 0:
        return None

    for index, (threshold, flag, tag) in enumerate(REMIND_STAGES):
        if remain <= threshold:
            if item.get(flag, False):
                return None

            return index, tag

    return None

def mark_current_and_wider_stages(item, current_index: int):
    for _, flag, _ in REMIND_STAGES[current_index:]:
        item[flag] = True