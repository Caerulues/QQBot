import re
from pathlib import Path
from typing import Optional

from nonebot import get_bot, logger, require

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler


# =========================
# 配置区
# =========================

from core.config import config

GROUP_ID = config.qq.event_group_id
MC_LOG_PATH = Path(config.minecraft.log_path)

# 定时任务 ID
JOB_ID = "minecraft_event_monitor"

# 检查日志间隔，单位：秒
CHECK_INTERVAL_SECONDS = 1

# QQ 群显示前缀
MC_PREFIX = "[MC]"

# 是否把死亡消息翻译为中文
TRANSLATE_DEATH_MESSAGE = True


# =========================
# 基础文本处理
# =========================

def clean_mc_text(text: str) -> str:
    """
    去掉 Minecraft 颜色代码。
    """
    return re.sub(r"§.", "", text).strip()


def strip_log_prefix(line: str) -> str:
    """
    去掉 latest.log 的日志前缀，只保留实际消息。

    示例：
    [21:24:18] [Server thread/INFO]: Steve joined the game
    -> Steve joined the game
    """
    line = clean_mc_text(line)

    # 标准日志：
    # [21:24:18] [Server thread/INFO]: xxx
    line = re.sub(r"^\[[^\]]+\] \[[^\]]+\]:\s*", "", line)

    # 少数日志可能是：
    # [Server thread/INFO]: xxx
    line = re.sub(r"^\[[^\]]+\]:\s*", "", line)

    return line.strip()


def is_player_name(name: str) -> bool:
    """
    Minecraft Java 正版玩家名通常为 3-16 位。
    为兼容离线服，这里允许 1-16 位。
    """
    return bool(re.fullmatch(r"[A-Za-z0-9_]{1,16}", name))


def normalize_death_text(text: str) -> str:
    """
    统一英文死亡消息里的一些变体。
    """
    text = text.replace(" while trying to escape ", " whilst trying to escape ")
    text = text.replace(" while fighting ", " whilst fighting ")
    return text.strip()


# =========================
# 进服 / 退服
# =========================

JOIN_PATTERN = re.compile(r"^([A-Za-z0-9_]{1,16}) joined the game$")
LEAVE_PATTERN = re.compile(r"^([A-Za-z0-9_]{1,16}) left the game$")


# =========================
# 死亡信息翻译
# =========================

def translate_death_message(msg: str) -> Optional[str]:
    """
    将 latest.log 中的英文死亡消息转成中文。

    说明：
    1. latest.log 通常仍然输出英文死亡消息。
    2. 这里按中文 Minecraft Wiki 的死亡消息含义整理为正则规则。
    3. Fabric Mod 自定义死亡消息无法保证全部覆盖。
    4. 如果无法识别，则返回 None。
    """
    msg = normalize_death_text(msg)

    name_pattern = r"(?P<dead>[A-Za-z0-9_]{1,16})"
    target_pattern = r"(?P<killer>.+?)"
    item_pattern = r"(?P<item>.+?)"

    rules: list[tuple[re.Pattern, str]] = [
        # =========================
        # 指令
        # =========================

        (
            re.compile(rf"^{name_pattern} was killed$"),
            "{dead} 被杀死了",
        ),

        # =========================
        # 近战 / 生物 / 玩家
        # =========================

        (
            re.compile(rf"^{name_pattern} was slain by {target_pattern} using {item_pattern}$"),
            "{dead} 被 {killer} 用 {item} 杀死了",
        ),
        (
            re.compile(rf"^{name_pattern} was slain by {target_pattern}$"),
            "{dead} 被 {killer} 杀死了",
        ),
        (
            re.compile(rf"^{name_pattern} was killed by {target_pattern} using {item_pattern}$"),
            "{dead} 被 {killer} 用 {item} 杀死了",
        ),
        (
            re.compile(rf"^{name_pattern} was killed by {target_pattern}$"),
            "{dead} 被 {killer} 杀死了",
        ),
        (
            re.compile(rf"^{name_pattern} was killed trying to hurt {target_pattern} using {item_pattern}$"),
            "{dead} 在试图伤害 {killer} 时被 {item} 杀死",
        ),
        (
            re.compile(rf"^{name_pattern} was killed trying to hurt {target_pattern}$"),
            "{dead} 在试图伤害 {killer} 时被杀死",
        ),
        (
            re.compile(rf"^{name_pattern} died because of {target_pattern}$"),
            "{dead} 死于 {killer}",
        ),
        (
            re.compile(rf"^{name_pattern} died$"),
            "{dead} 死了",
        ),

        # =========================
        # 蜜蜂 / 螫刺
        # =========================

        (
            re.compile(rf"^{name_pattern} was stung to death by {target_pattern} using {item_pattern}$"),
            "{dead} 被 {killer} 用 {item} 蛰死了",
        ),
        (
            re.compile(rf"^{name_pattern} was stung to death by {target_pattern}$"),
            "{dead} 被 {killer} 蛰死了",
        ),
        (
            re.compile(rf"^{name_pattern} was stung to death$"),
            "{dead} 被蛰死了",
        ),

        # =========================
        # 弓箭 / 投射物 / 头颅 / 三叉戟 / 火球
        # =========================

        (
            re.compile(rf"^{name_pattern} was shot by a skull from {target_pattern} using {item_pattern}$"),
            "{dead} 被 {killer} 用 {item} 发射的头颅射杀",
        ),
        (
            re.compile(rf"^{name_pattern} was shot by a skull from {target_pattern}$"),
            "{dead} 被 {killer} 发射的头颅射杀",
        ),
        (
            re.compile(rf"^{name_pattern} was shot by {target_pattern} using {item_pattern}$"),
            "{dead} 被 {killer} 用 {item} 射杀",
        ),
        (
            re.compile(rf"^{name_pattern} was shot by {target_pattern}$"),
            "{dead} 被 {killer} 射杀",
        ),
        (
            re.compile(rf"^{name_pattern} was shot$"),
            "{dead} 被射杀了",
        ),
        (
            re.compile(rf"^{name_pattern} was impaled by {target_pattern} using {item_pattern}$"),
            "{dead} 被 {killer} 用 {item} 刺穿了",
        ),
        (
            re.compile(rf"^{name_pattern} was impaled by {target_pattern}$"),
            "{dead} 被 {killer} 刺穿了",
        ),
        (
            re.compile(rf"^{name_pattern} was fireballed by {target_pattern} using {item_pattern}$"),
            "{dead} 被 {killer} 用 {item} 发射的火球击杀",
        ),
        (
            re.compile(rf"^{name_pattern} was fireballed by {target_pattern}$"),
            "{dead} 被 {killer} 发射的火球击杀",
        ),
        (
            re.compile(rf"^{name_pattern} was spitballed by {target_pattern}$"),
            "{dead} 被 {killer} 吐出的唾沫击杀",
        ),
        (
            re.compile(rf"^{name_pattern} was pummeled by {target_pattern}$"),
            "{dead} 被 {killer} 击中身亡",
        ),
        (
            re.compile(rf"^{name_pattern} was skewered by {target_pattern}$"),
            "{dead} 被 {killer} 刺穿了",
        ),
        (
            re.compile(rf"^{name_pattern} was destroyed by {target_pattern}$"),
            "{dead} 被 {killer} 摧毁了",
        ),

        # =========================
        # 爆炸 / 床 / 重生锚
        # =========================

        (
            re.compile(rf"^{name_pattern} was blown up by {target_pattern} using {item_pattern}$"),
            "{dead} 被 {killer} 用 {item} 炸死了",
        ),
        (
            re.compile(rf"^{name_pattern} was blown up by {target_pattern}$"),
            "{dead} 被 {killer} 炸死了",
        ),
        (
            re.compile(rf"^{name_pattern} was blown up$"),
            "{dead} 爆炸了",
        ),
        (
            re.compile(rf"^{name_pattern} blew up$"),
            "{dead} 爆炸了",
        ),
        (
            re.compile(rf"^{name_pattern} was killed by \[Intentional Game Design\]$"),
            "{dead} 被[刻意的游戏设计]杀死了",
        ),
        (
            re.compile(rf"^{name_pattern} was obliterated by {target_pattern}$"),
            "{dead} 被 {killer} 抹除了",
        ),

        # =========================
        # 烟花
        # =========================

        (
            re.compile(rf"^{name_pattern} went off with a bang whilst fighting {target_pattern}$"),
            "{dead} 在与 {killer} 战斗时随着一声巨响消失了",
        ),
        (
            re.compile(rf"^{name_pattern} went off with a bang$"),
            "{dead} 随着一声巨响消失了",
        ),
        (
            re.compile(rf"^{name_pattern} went off with a bang due to a firework fired from {target_pattern} by {item_pattern}$"),
            "{dead} 随着 {target} 用 {item} 发射的烟花发出的巨响消失了",
        ),

        # =========================
        # 仙人掌 / 甜浆果 / 尖刺
        # =========================

        (
            re.compile(rf"^{name_pattern} walked into a cactus whilst trying to escape {target_pattern}$"),
            "{dead} 在试图逃离 {killer} 时撞上了仙人掌",
        ),
        (
            re.compile(rf"^{name_pattern} walked into a cactus$"),
            "{dead} 撞上了仙人掌",
        ),
        (
            re.compile(rf"^{name_pattern} was pricked to death$"),
            "{dead} 被刺死了",
        ),
        (
            re.compile(rf"^{name_pattern} was poked to death by a sweet berry bush whilst trying to escape {target_pattern}$"),
            "{dead} 在试图逃离 {killer} 时被甜浆果丛刺死了",
        ),
        (
            re.compile(rf"^{name_pattern} was poked to death by a sweet berry bush$"),
            "{dead} 被甜浆果丛刺死了",
        ),
        (
            re.compile(rf"^{name_pattern} was poked to death$"),
            "{dead} 被戳死了",
        ),
        (
            re.compile(rf"^{name_pattern} was killed while trying to hurt {target_pattern}$"),
            "{dead} 在试图伤害 {killer} 时被杀死",
        ),

        # =========================
        # 溺水 / 脱水
        # =========================

        (
            re.compile(rf"^{name_pattern} drowned whilst trying to escape {target_pattern}$"),
            "{dead} 在试图逃离 {killer} 时淹死了",
        ),
        (
            re.compile(rf"^{name_pattern} drowned$"),
            "{dead} 淹死了",
        ),
        (
            re.compile(rf"^{name_pattern} died from dehydration whilst trying to escape {target_pattern}$"),
            "{dead} 在试图逃离 {killer} 时因脱水而死",
        ),
        (
            re.compile(rf"^{name_pattern} died from dehydration$"),
            "{dead} 因脱水而死",
        ),
        (
            re.compile(rf"^{name_pattern} was killed by dryout$"),
            "{dead} 因脱水而死",
        ),

        # =========================
        # 鞘翅 / 动能 / 撞墙
        # =========================

        (
            re.compile(rf"^{name_pattern} experienced kinetic energy whilst trying to escape {target_pattern}$"),
            "{dead} 在试图逃离 {killer} 时感受到了动能",
        ),
        (
            re.compile(rf"^{name_pattern} experienced kinetic energy$"),
            "{dead} 感受到了动能",
        ),
        (
            re.compile(rf"^{name_pattern} flew into a wall whilst fighting {target_pattern}$"),
            "{dead} 在与 {killer} 战斗时飞进了墙里",
        ),
        (
            re.compile(rf"^{name_pattern} flew into a wall$"),
            "{dead} 飞进了墙里",
        ),

        # =========================
        # 坠落
        # =========================

        (
            re.compile(rf"^{name_pattern} hit the ground too hard whilst trying to escape {target_pattern}$"),
            "{dead} 在试图逃离 {killer} 时落地过猛",
        ),
        (
            re.compile(rf"^{name_pattern} hit the ground too hard$"),
            "{dead} 落地过猛",
        ),
        (
            re.compile(rf"^{name_pattern} fell from a high place$"),
            "{dead} 从高处摔了下来",
        ),
        (
            re.compile(rf"^{name_pattern} fell off a ladder$"),
            "{dead} 从梯子上摔了下来",
        ),
        (
            re.compile(rf"^{name_pattern} fell off some vines$"),
            "{dead} 从藤蔓上摔了下来",
        ),
        (
            re.compile(rf"^{name_pattern} fell off some weeping vines$"),
            "{dead} 从垂泪藤上摔了下来",
        ),
        (
            re.compile(rf"^{name_pattern} fell off some twisting vines$"),
            "{dead} 从缠怨藤上摔了下来",
        ),
        (
            re.compile(rf"^{name_pattern} fell off scaffolding$"),
            "{dead} 从脚手架上摔了下来",
        ),
        (
            re.compile(rf"^{name_pattern} fell while climbing$"),
            "{dead} 在攀爬时摔了下来",
        ),
        (
            re.compile(rf"^{name_pattern} was doomed to fall by {target_pattern} using {item_pattern}$"),
            "{dead} 被 {killer} 用 {item} 击中，注定要摔死",
        ),
        (
            re.compile(rf"^{name_pattern} was doomed to fall by {target_pattern}$"),
            "{dead} 被 {killer} 击中，注定要摔死",
        ),
        (
            re.compile(rf"^{name_pattern} was doomed to fall$"),
            "{dead} 注定要摔死",
        ),
        (
            re.compile(rf"^{name_pattern} fell too far and was finished by {target_pattern} using {item_pattern}$"),
            "{dead} 摔得太重后被 {killer} 用 {item} 了结了",
        ),
        (
            re.compile(rf"^{name_pattern} fell too far and was finished by {target_pattern}$"),
            "{dead} 摔得太重后被 {killer} 了结了",
        ),
        (
            re.compile(rf"^{name_pattern} fell too far$"),
            "{dead} 摔得太远了",
        ),
        (
            re.compile(rf"^{name_pattern} was impaled on a stalagmite whilst fighting {target_pattern}$"),
            "{dead} 在与 {killer} 战斗时被石笋刺穿了",
        ),
        (
            re.compile(rf"^{name_pattern} was impaled on a stalagmite$"),
            "{dead} 被石笋刺穿了",
        ),
        (
            re.compile(rf"^{name_pattern} death\.fell\.accident\.water$"),
            "{dead} 在水中摔死了",
        ),

        # =========================
        # 坠落方块 / 铁砧 / 钟乳石
        # =========================

        (
            re.compile(rf"^{name_pattern} was squashed by a falling anvil whilst fighting {target_pattern}$"),
            "{dead} 在与 {killer} 战斗时被坠落的铁砧压扁了",
        ),
        (
            re.compile(rf"^{name_pattern} was squashed by a falling anvil$"),
            "{dead} 被坠落的铁砧压扁了",
        ),
        (
            re.compile(rf"^{name_pattern} was squashed by a falling block whilst fighting {target_pattern}$"),
            "{dead} 在与 {killer} 战斗时被下落的方块压扁了",
        ),
        (
            re.compile(rf"^{name_pattern} was squashed by a falling block$"),
            "{dead} 被下落的方块压扁了",
        ),
        (
            re.compile(rf"^{name_pattern} was skewered by a falling stalactite whilst fighting {target_pattern}$"),
            "{dead} 在与 {killer} 战斗时被坠落的钟乳石刺穿了",
        ),
        (
            re.compile(rf"^{name_pattern} was skewered by a falling stalactite$"),
            "{dead} 被坠落的钟乳石刺穿了",
        ),
        (
            re.compile(rf"^{name_pattern} was smashed by falling stalactite$"),
            "{dead} 被坠落的钟乳石砸死了",
        ),
        (
            re.compile(rf"^{name_pattern} was crushed by a falling tree$"),
            "{dead} 被倒下的树压死了",
        ),

        # =========================
        # 火焰 / 火 / 岩浆 / 岩浆块
        # =========================

        (
            re.compile(rf"^{name_pattern} went up in flames$"),
            "{dead} 被火焰吞没了",
        ),
        (
            re.compile(rf"^{name_pattern} walked into fire whilst fighting {target_pattern}$"),
            "{dead} 在与 {killer} 战斗时走进了火中",
        ),
        (
            re.compile(rf"^{name_pattern} walked into fire$"),
            "{dead} 走进了火中",
        ),
        (
            re.compile(rf"^{name_pattern} burned to death$"),
            "{dead} 被烧死了",
        ),
        (
            re.compile(rf"^{name_pattern} was burnt to a crisp whilst fighting {target_pattern}$"),
            "{dead} 在与 {killer} 战斗时被烧成了灰烬",
        ),
        (
            re.compile(rf"^{name_pattern} was burnt to a crisp$"),
            "{dead} 被烧成了灰烬",
        ),
        (
            re.compile(rf"^{name_pattern} was burned to a crisp whilst fighting {target_pattern}$"),
            "{dead} 在与 {killer} 战斗时被烧成了灰烬",
        ),
        (
            re.compile(rf"^{name_pattern} was burned to a crisp$"),
            "{dead} 被烧成了灰烬",
        ),
        (
            re.compile(rf"^{name_pattern} tried to swim in lava to escape {target_pattern}$"),
            "{dead} 试图在岩浆里游泳以逃离 {killer}",
        ),
        (
            re.compile(rf"^{name_pattern} tried to swim in lava$"),
            "{dead} 试图在岩浆里游泳",
        ),
        (
            re.compile(rf"^{name_pattern} discovered the floor was lava whilst fighting {target_pattern}$"),
            "{dead} 在与 {killer} 战斗时发现地板是岩浆",
        ),
        (
            re.compile(rf"^{name_pattern} discovered the floor was lava$"),
            "{dead} 发现地板是岩浆",
        ),
        (
            re.compile(rf"^{name_pattern} walked into danger zone due to {target_pattern}$"),
            "{dead} 因为 {killer} 而走进了危险区域",
        ),
        (
            re.compile(rf"^{name_pattern} walked into the danger zone$"),
            "{dead} 走进了危险区域",
        ),

        # =========================
        # 闪电
        # =========================

        (
            re.compile(rf"^{name_pattern} was struck by lightning whilst fighting {target_pattern}$"),
            "{dead} 在与 {killer} 战斗时被闪电击中",
        ),
        (
            re.compile(rf"^{name_pattern} was struck by lightning$"),
            "{dead} 被闪电击中",
        ),

        # =========================
        # 魔法 / 龙息 / 凋零 / 饥饿
        # =========================

        (
            re.compile(rf"^{name_pattern} was killed by magic whilst trying to escape {target_pattern}$"),
            "{dead} 在试图逃离 {killer} 时被魔法杀死了",
        ),
        (
            re.compile(rf"^{name_pattern} was killed by even more magic$"),
            "{dead} 被更强大的魔法杀死了",
        ),
        (
            re.compile(rf"^{name_pattern} was killed by magic$"),
            "{dead} 被魔法杀死了",
        ),
        (
            re.compile(rf"^{name_pattern} was roasted in dragon breath by {target_pattern}$"),
            "{dead} 被 {killer} 的龙息烤熟了",
        ),
        (
            re.compile(rf"^{name_pattern} was roasted in dragon breath$"),
            "{dead} 被龙息烤熟了",
        ),
        (
            re.compile(rf"^{name_pattern} withered away whilst fighting {target_pattern}$"),
            "{dead} 在与 {killer} 战斗时凋零了",
        ),
        (
            re.compile(rf"^{name_pattern} withered away$"),
            "{dead} 凋零了",
        ),
        (
            re.compile(rf"^{name_pattern} starved to death whilst fighting {target_pattern}$"),
            "{dead} 在与 {killer} 战斗时饿死了",
        ),
        (
            re.compile(rf"^{name_pattern} starved to death$"),
            "{dead} 饿死了",
        ),

        # =========================
        # 细雪 / 冻结
        # =========================

        (
            re.compile(rf"^{name_pattern} was frozen to death by {target_pattern} using {item_pattern}$"),
            "{dead} 被 {killer} 用 {item} 冻死了",
        ),
        (
            re.compile(rf"^{name_pattern} was frozen to death by {target_pattern}$"),
            "{dead} 被 {killer} 冻死了",
        ),
        (
            re.compile(rf"^{name_pattern} froze to death$"),
            "{dead} 冻死了",
        ),

        # =========================
        # 监守者 / 音波尖啸
        # =========================

        (
            re.compile(rf"^{name_pattern} was obliterated by a sonically-charged shriek whilst trying to escape {target_pattern}$"),
            "{dead} 在试图逃离 {killer} 时被一道音波尖啸抹除了",
        ),
        (
            re.compile(rf"^{name_pattern} was obliterated by a sonically-charged shriek$"),
            "{dead} 被一道音波尖啸抹除了",
        ),
        (
            re.compile(rf"^{name_pattern} was killed by sonic boom whilst trying to escape {target_pattern}$"),
            "{dead} 在试图逃离 {killer} 时被一道音波尖啸抹除了",
        ),
        (
            re.compile(rf"^{name_pattern} was killed by sonic boom$"),
            "{dead} 被一道音波尖啸抹除了",
        ),

        # =========================
        # 窒息 / 实体挤压 / 世界边界
        # =========================

        (
            re.compile(rf"^{name_pattern} suffocated in a wall whilst fighting {target_pattern}$"),
            "{dead} 在与 {killer} 战斗时在墙里窒息了",
        ),
        (
            re.compile(rf"^{name_pattern} suffocated in a wall$"),
            "{dead} 在墙里窒息了",
        ),
        (
            re.compile(rf"^{name_pattern} was squished too much whilst fighting {target_pattern}$"),
            "{dead} 在与 {killer} 战斗时被过度挤压了",
        ),
        (
            re.compile(rf"^{name_pattern} was squished too much$"),
            "{dead} 被过度挤压了",
        ),
        (
            re.compile(rf"^{name_pattern} left the confines of this world whilst fighting {target_pattern}$"),
            "{dead} 在与 {killer} 战斗时离开了这个世界的边界",
        ),
        (
            re.compile(rf"^{name_pattern} left the confines of this world$"),
            "{dead} 离开了这个世界的边界",
        ),

        # =========================
        # 虚空
        # =========================

        (
            re.compile(rf"^{name_pattern} didn't want to live in the same world as {target_pattern}$"),
            "{dead} 与 {killer} 不共戴天",
        ),
        (
            re.compile(rf"^{name_pattern} fell out of the world$"),
            "{dead} 掉出了这个世界",
        ),
        (
            re.compile(rf"^{name_pattern} was too soft for this world$"),
            "{dead} 对这个世界来说太脆弱了",
        ),
    ]

    for pattern, template in rules:
        match = pattern.match(msg)
        if match:
            data = match.groupdict()
            return template.format(**data)

    return None


def is_likely_death_message(msg: str) -> bool:
    """
    用于兜底判断是否可能是死亡消息。
    """
    msg = normalize_death_text(msg)

    first_word = msg.split(" ", 1)[0] if " " in msg else ""

    if not is_player_name(first_word):
        return False

    keywords = [
        " died",
        " died because of",
        " was killed",
        " was slain by",
        " was stung",
        " was shot",
        " was impaled",
        " was fireballed",
        " was spitballed",
        " was pummeled",
        " was skewered",
        " was destroyed",
        " was blown up",
        " blew up",
        " went off with a bang",
        " walked into a cactus",
        " was pricked",
        " was poked",
        " drowned",
        " died from dehydration",
        " was killed by dryout",
        " experienced kinetic energy",
        " flew into a wall",
        " hit the ground too hard",
        " fell from",
        " fell off",
        " fell while",
        " was doomed to fall",
        " fell too far",
        " was impaled on a stalagmite",
        " was squashed",
        " was skewered by a falling stalactite",
        " was smashed by falling stalactite",
        " was crushed by a falling tree",
        " went up in flames",
        " walked into fire",
        " burned to death",
        " was burnt to a crisp",
        " was burned to a crisp",
        " tried to swim in lava",
        " discovered the floor was lava",
        " walked into danger zone",
        " walked into the danger zone",
        " was struck by lightning",
        " was killed by magic",
        " was killed by even more magic",
        " was roasted in dragon breath",
        " withered away",
        " starved to death",
        " was frozen",
        " froze to death",
        " was obliterated by a sonically-charged shriek",
        " was killed by sonic boom",
        " suffocated in a wall",
        " was squished too much",
        " left the confines",
        " didn't want to live",
        " fell out of the world",
        " was too soft",
        " death.fell.accident.water",
    ]

    return any(keyword in msg for keyword in keywords)


# =========================
# 事件解析
# =========================

def parse_mc_event(line: str) -> Optional[str]:
    """
    解析 latest.log 的一行。

    返回：
    - 需要发送到 QQ 群的消息
    - 不需要转发时返回 None
    """
    msg = strip_log_prefix(line)

    if not msg:
        return None

    # 排除 spark 输出
    if msg.startswith("[⚡]"):
        return None

    # 排除 RCON 连接日志
    if "RCON Client" in line:
        return None

    # 排除常见非玩家事件日志
    ignored_prefixes = (
        "Thread ",
        "Saving ",
        "Saved ",
        "Time elapsed:",
        "Done ",
        "Starting ",
        "Stopping ",
        "Loading ",
        "Preparing ",
        "Unknown command",
        "There are ",
        "Found ",
        "Disconnecting ",
        "UUID of player ",
        "Player ",
        "com.mojang",
        "net.minecraft",
        "java.",
    )

    if msg.startswith(ignored_prefixes):
        return None

    # 玩家加入
    join_match = JOIN_PATTERN.match(msg)
    if join_match:
        name = join_match.group(1)
        return f"{MC_PREFIX} {name} 加入了服务器"

    # 玩家离开
    leave_match = LEAVE_PATTERN.match(msg)
    if leave_match:
        name = leave_match.group(1)
        return f"{MC_PREFIX} {name} 离开了服务器"

    # 死亡消息
    if TRANSLATE_DEATH_MESSAGE:
        translated = translate_death_message(msg)
        if translated:
            return f"{MC_PREFIX} {translated}"

    # 未翻译成功，但看起来像死亡消息，则原样转发
    if is_likely_death_message(msg):
        return f"{MC_PREFIX} {msg}"

    return None


# =========================
# latest.log 增量读取
# =========================

class LogTailer:
    """
    latest.log 增量读取器。

    启动时跳到文件末尾，避免旧日志刷屏。
    后续每次只读取新增内容。
    """

    def __init__(self, path: Path):
        self.path = path
        self.position = 0
        self.initialized = False

    def init_position(self):
        if self.path.exists():
            self.position = self.path.stat().st_size
        else:
            self.position = 0

        self.initialized = True

    def read_new_lines(self) -> list[str]:
        if not self.initialized:
            self.init_position()
            return []

        if not self.path.exists():
            self.position = 0
            return []

        current_size = self.path.stat().st_size

        # latest.log 被重建或截断
        if current_size < self.position:
            self.position = 0

        with self.path.open("r", encoding="utf-8", errors="ignore") as f:
            f.seek(self.position)
            lines = f.readlines()
            self.position = f.tell()

        return lines


tailer = LogTailer(MC_LOG_PATH)


# =========================
# 定时监听任务
# =========================

async def check_minecraft_events():
    if GROUP_ID is None:
        return

    try:
        lines = tailer.read_new_lines()

        if not lines:
            return

        bot = get_bot()

        for line in lines:
            message = parse_mc_event(line)

            if not message:
                continue

            await bot.send_group_msg(
                group_id=GROUP_ID,
                message=message
            )

    except Exception as e:
        logger.warning(f"Minecraft事件转发失败: {e}")


if scheduler.get_job(JOB_ID):
    scheduler.remove_job(JOB_ID)

scheduler.add_job(
    check_minecraft_events,
    "interval",
    seconds=CHECK_INTERVAL_SECONDS,
    id=JOB_ID,
)