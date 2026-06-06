# QQBot: Cauxium

<p align="center">
  <strong>一个面向个人 Minecraft 群服的 QQ 服务器管理 Bot</strong>
</p>

<p align="center">
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-blue">
  <img alt="NoneBot" src="https://img.shields.io/badge/NoneBot-2.x-green">
  <img alt="OneBot" src="https://img.shields.io/badge/OneBot-v11-orange">
  <img alt="Platform" src="https://img.shields.io/badge/Platform-macOS-lightgrey">
  <img alt="Minecraft" src="https://img.shields.io/badge/Minecraft-Java%20Server-brightgreen">
</p>

---

## 项目简介

**Cauxium** 是一个基于 **NoneBot2** 和 **OneBot v11** 协议开发的 QQBot，主要用于在 QQ 群中远程管理、监控和联动本地 Minecraft Java 服务器。

通过 QQ 群指令，用户可以启动或关闭 Minecraft 服务器、查询服务器状态、查看在线玩家、同步 QQ 与 Minecraft 聊天、监听玩家进出和死亡事件，并在 IPv6 地址变化时自动通知群成员。

本项目的定位是一个偏向 **Minecraft 群服互联 + QQ 群辅助**。

---

## 功能特性

### Minecraft 服务器管理

- 通过 QQ 指令启动 Minecraft Java 服务器
- 通过 QQ 指令向服务器终端发送 `stop` 并关闭服务器
- 自动检测本机是否已有 Java / `server.jar` 进程
- 自动记录并恢复 macOS Terminal 的 Minecraft 服务器窗口 ID
- 支持通过 AppleScript 新建 Terminal 窗口并执行启动命令

### Minecraft 状态查询

- 查询服务器是否在线
- 查询服务器名称、版本、端口和在线人数
- 查询在线玩家列表
- 查询出站 IPv6 网络延迟
- 通过 RCON 获取服务器 TPS / MSPT
- 支持 spark 输出解析

### QQ 与 Minecraft 消息互通

- QQ 群消息转发到 Minecraft 服务器内
- Minecraft 玩家聊天转发到 QQ 群
- 自动过滤 QQ 指令，避免命令内容进入游戏聊天
- 防止 QQ 与 Minecraft 消息互相回流导致循环转发

### Minecraft 事件通知

- 玩家加入服务器通知
- 玩家离开服务器通知
- 玩家死亡事件通知
- 常见英文死亡信息中文化处理
- 支持将事件推送到指定 QQ 群

### IPv6 地址监控

- 手动查询当前 IPv6 地址
- Minecraft 服务器启动后自动发送当前 IPv6 地址
- 每 10 分钟检查一次 IPv6 是否变化
- IPv6 更新后自动通知 QQ 群
- 适合家庭宽带 IPv6 地址动态变化的场景

### DDL 截止日期提醒

- 添加截止日期任务
- 查看任务列表
- 删除任务
- 支持中文时间解析
- 支持生成图片形式的任务列表
- 到期前一周、一天、一小时自动提醒
- 过期任务自动清理

### QQBot 辅助功能

- `.help` 帮助菜单
- `.echo` 在线测试
- `.ping` 消息延迟测试
- `.status` 系统状态查询
- 群聊复读功能
- 用户撤回消息后，Bot 自动撤回对应回复

---

## 技术栈

| 模块 | 技术 |
| --- | --- |
| Bot 框架 | NoneBot2 |
| QQ 协议 | OneBot v11 |
| QQ 客户端实现 | NapCat / Lagrange / go-cqhttp 等 |
| 服务器控制 | Python `asyncio`、AppleScript、macOS Terminal |
| Minecraft 状态查询 | `mcstatus` |
| Minecraft 控制台交互 | RCON |
| 定时任务 | `nonebot-plugin-apscheduler` |
| 系统状态 | `psutil` |
| 中文时间解析 | `jionlp`、`dateparser` |
| 图片生成 | Pillow |
| 配置格式 | TOML |

---

## 项目结构

```text
.
├── bot.py                  # NoneBot 启动入口
├── config.toml             # 本地配置文件，不建议上传 GitHub
├── config_example.toml     # 配置模板，建议补全后提交到仓库
├── .env                    # NoneBot 环境变量
├── .gitignore              # Git 忽略规则
│
├── core/                   # 核心逻辑
│   ├── config.py           # 读取 config.toml
│   ├── ipv6.py             # 获取本机 IPv6 地址
│   ├── java_monitor.py     # 检测 Java / Minecraft 进程
│   ├── terminal_control.py # macOS Terminal 控制
│   ├── terminal_state.py   # 记录服务器 Terminal 窗口 ID
│   └── time_regex.py       # 中文时间提取规则
│
├── plugins/                # QQ 指令插件
│   ├── server.py           # .run_server / .stop_server
│   ├── ddl.py              # .ddl 截止日期管理
│   ├── help.py             # .help 帮助菜单
│   ├── echo.py             # .echo 测试
│   ├── ping.py             # .ping 延迟测试
│   ├── status.py           # .status 系统状态
│   └── ipv6_cmd.py         # .ipv6 查询 IPv6
│
├── mcserver/               # Minecraft 联动逻辑
│   ├── mc_info.py          # .mcinfo 服务器信息查询
│   ├── mc_bridge.py        # QQ 与 Minecraft 聊天互通
│   └── mc_events.py        # 进服、退服、死亡事件监听
│
├── utils/                  # 通用工具
│   ├── auto_add_one.py     # 群聊复读
│   ├── ipv6_monitor.py     # IPv6 定时监控
│   ├── recall.py           # 撤回联动
│   ├── recall_map.py       # 消息 ID 映射
│   └── safe_send.py        # 发送消息并记录撤回映射
│
└── data/                   # 运行时数据目录
    ├── deadlines/          # DDL 数据
    ├── ip/                 # IPv6 记录
    └── server_terminal.json# Minecraft Terminal 窗口记录
```

---

## 运行环境

建议环境：

- macOS / Linux / Windows
- Python 3.11+
- Minecraft Java Edition Server
- 已配置好的 OneBot v11 客户端，例如 NapCat
- 已安装 Java 运行环境
- Minecraft 服务端已开启 RCON

如果需要使用 `.run_server` 和 `.stop_server`，必须在 macOS 上运行，因为当前服务器启动和停止逻辑依赖 AppleScript 与 Terminal。

Windows 或 Linux 可以复用大部分查询、RCON、聊天互通和事件监听逻辑，但需要重写 `core/terminal_control.py` 中的终端控制部分。

---

## 安装依赖

建议先创建虚拟环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
```

安装项目所需依赖：

```bash
pip install nonebot2
pip install nonebot-adapter-onebot
pip install nonebot-plugin-apscheduler
pip install python-dotenv
pip install psutil
pip install mcstatus
pip install mcrcon
pip install pillow
pip install dateparser
pip install jionlp
```

---

## 配置说明

项目根目录需要 `.env` 和 `config.toml` 两个配置文件。

### `.env`

示例：

```env
HOST=127.0.0.1
PORT=8080
COMMAND_START=["."]
```

其中 `COMMAND_START=["."]` 表示 Bot 指令以前缀 `.` 开始，例如 `.help`、`.ddl`、`.mcinfo`。

### `config.toml`

示例(config_example.toml)：

```toml
data_dir = "data"

[server]
path = ""
command = "java -Xms1024M -Xmx4096M -jar server.jar nogui"
terminal_title = "MINECRAFT_SERVER_TERMINAL"

[rcon]
host = "127.0.0.1"
port = 25575
password = ""

[minecraft]
port = 25565
name = ""
status_address = "127.0.0.1:25565"
log_path = "/path/to/minecraft/server/logs/latest.log"
ping_target = ""

[qq]
admin_users = []
groups = []
bridge_group_id = 0
event_group_id = 0
bot_ids = []
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| `data_dir` | Bot 运行时数据保存目录 |
| `server.path` | Minecraft 服务端所在目录 |
| `server.command` | Minecraft 服务端启动命令 |
| `server.terminal_title` | 用于识别服务器 Terminal 窗口的标题 |
| `rcon.host` | RCON 地址，通常为 `127.0.0.1` |
| `rcon.port` | RCON 端口 |
| `rcon.password` | RCON 密码 |
| `minecraft.port` | Minecraft 服务器端口 |
| `minecraft.name` | 服务器显示名称 |
| `minecraft.status_address` | `mcstatus` 查询地址 |
| `minecraft.log_path` | `latest.log` 日志路径 |
| `minecraft.ping_target` | IPv6 网络延迟测试目标 |
| `qq.admin_users` | 允许启动 / 停止服务器的 QQ 用户 |
| `qq.groups` | 允许 Bot 响应和发送通知的群 |
| `qq.bridge_group_id` | QQ-Minecraft 聊天互通群 |
| `qq.event_group_id` | Minecraft 事件通知群 |
| `qq.bot_ids` | Bot 自己的 QQ 号，用于避免重复处理自己的消息 |

---

## Minecraft 服务端配置

如果需要使用 RCON 和 TPS 查询，请在 Minecraft 服务端的 `server.properties` 中开启 RCON：

```properties
enable-rcon=true
rcon.port=25575
rcon.password=your_rcon_password
```

如果需要查询 TPS / MSPT，服务器内还需要安装 spark，并确保 RCON 执行以下命令时能够输出结果：

```text
spark tps
```

如果只需要基础在线状态查询，可以不配置 spark。

---

## 启动项目

先启动 OneBot v11 客户端，例如 NapCat，并确认它能够连接到 NoneBot。

然后在项目根目录运行：

```bash
python bot.py
```

如果使用 PyCharm，可以将 `bot.py` 设置为运行入口。

启动成功后，Bot 会加载：

```text
core/
utils/
plugins/
mcserver/
```

并自动注册所有指令、事件监听和定时任务。

---

## 指令列表

### 基础指令

| 指令 | 功能 |
| --- | --- |
| `.help` | 查看帮助菜单 |
| `.echo <内容>` | 测试 Bot 是否在线 |
| `.ping` | 测试消息接收与发送延迟 |
| `.status` | 查看 Bot 所在设备的 CPU、内存和运行时间 |
| `.ipv6` | 查询当前 IPv6 地址 |

### Minecraft 指令

| 指令 | 功能 |
| --- | --- |
| `.run_server` | 启动 Minecraft 服务器 |
| `.stop_server` | 停止 Minecraft 服务器 |
| `.mcinfo` | 查询 Minecraft 服务器状态 |

### DDL 指令

| 指令 | 功能 |
| --- | --- |
| `.ddl add <任务名称> <截止时间>` | 添加截止日期任务 |
| `.ddl list` | 查看任务列表 |
| `.ddl del <UUID>` | 删除任务 |
| `.ddl help` | 查看 DDL 帮助 |

示例：

```text
.ddl add 数学作业 明天下午5点
.ddl list
.ddl del ab12cd34
```

---

## 使用示例

### 启动服务器

```text
.run_server
```

可能返回：

```text
Minecraft Server已启动
```

如果服务器已经在运行：

```text
Minecraft Server已在运行
```

如果不是管理员：

```text
Process Denied
```

### 停止服务器

```text
.stop_server
```

Bot 会向服务器 Terminal 发送：

```text
stop
```

然后等待 Java 服务端进程结束。

### 查询服务器信息

```text
.mcinfo
```

可能返回：

```text
Subgroup Server(1.21.1)
在线: 2/20 出站延迟: 35ms
TPS: 20.0, MSPT: 8.5
玩家: Steve
```

### IPv6 更新通知

服务器启动后，Bot 会向配置群发送：

```text
服务器IPv6地址如下
[xxxx:xxxx:xxxx:xxxx::xxxx]:25565
```

如果后续 IPv6 改变：

```text
服务器IPv6地址已更新
[xxxx:xxxx:xxxx:xxxx::yyyy]:25565
```

### QQ 与 Minecraft 互通

QQ 群消息会转发到 Minecraft：

```text
[QQ] 群名片：hello
```

Minecraft 玩家聊天会转发到 QQ：

```text
[MC] Steve：hello
```

---

## 数据保存

项目运行时会在 `data/` 目录下保存数据。

| 路径 | 用途 |
| --- | --- |
| `data/deadlines/` | 保存每个用户的 DDL 任务 |
| `data/ip/ipv6.json` | 保存上一次检测到的 IPv6 地址 |
| `data/server_terminal.json` | 保存 Minecraft Terminal 窗口 ID |

