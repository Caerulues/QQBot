# QQBot: Cauxium

<p>
  <strong>一个面向个人 Minecraft 群服的 QQ 服务器管理 Bot</strong>
</p>

<p>
  <img alt="Python" src="https://img.shields.io/badge/Python-3.11%2B-blue">
  <img alt="NoneBot" src="https://img.shields.io/badge/NoneBot-2.x-green">
  <img alt="OneBot" src="https://img.shields.io/badge/OneBot-v11-orange">
  <img alt="Platform" src="https://img.shields.io/badge/Platform-macOS-lightgrey">
  <img alt="Minecraft" src="https://img.shields.io/badge/Minecraft-Java%20Server-brightgreen">
</p>

一个基于 NoneBot2 + OneBot v11 的个人 QQ Bot，面向家庭 Minecraft 服务器管理与日常效率场景设计。

QQBot 提供 Minecraft 服务器启停、服务器状态查询、QQ ↔ Minecraft 消息互通、todo 管理、DDL 提醒、IPv6 状态查看等功能，适合部署在个人电脑、家庭服务器或小型群服环境中使用。

---

## 功能特性

### Minecraft 服务器管理

* 启动 Minecraft 服务器
* 停止 Minecraft 服务器
* 查询服务器在线状态
* 查看在线玩家列表
* 获取延迟、TPS、MSPT 等运行信息

### QQ &rarr; Minecraft 联动

* QQ 消息转发至 Minecraft 游戏内聊天
* Minecraft 聊天同步至 QQ
* 玩家加入服务器通知
* 玩家退出服务器通知
* 玩家死亡消息同步

### Todo 管理

* 添加待办事项
* 查看待办列表
* 标记任务完成
* 支持分区（Branch）管理
* 支持模糊搜索
* 支持撤销上一次操作

### DDL 提醒

* 添加截止日期任务
* 查看任务列表
* 删除任务
* 自动提醒

### 系统工具

* Bot 在线测试
* 网络延迟测试
* IPv6 地址查询
* 系统运行状态查看
* 帮助菜单

---

## 运行环境

推荐环境：

* Python 3.14+
* macOS（已在 macOS 上完成主要测试）
* QQ + NapCat
* NoneBot2
* OneBot v11

Minecraft 相关功能需要：

* Java 版 Minecraft 服务器
* 开启 RCON

---

## 快速开始

### 1. 克隆项目

```commandline
git clone https://github.com/Caerulues/QQBot.git
cd QQBot
```

### 2. 安装依赖

建议使用虚拟环境：

```commandline
python -m venv .venv
source .venv/bin/activate
```

安装依赖：

```commandline
pip install nonebot2
pip install nonebot-adapter-onebot
pip install nonebot-plugin-apscheduler
pip install fastapi uvicorn
pip install mcstatus mcrcon
pip install psutil pillow
pip install dateparser jionlp
```

---

### 配置 NapCat

安装 NapCat 后，配置 OneBot v11 反向 WebSocket。

示例配置：

```text
地址：
ws://127.0.0.1:8080/onebot/v11/ws
```

启动 NapCat 并确保 QQ 已登录。

---

### 配置 .env

创建 .env 文件：

```dotenv
DRIVER=~fastapi+~websockets
HOST=127.0.0.1
PORT=8080
COMMAND_START=["."]
SUPERUSERS=["123456789"]
ONEBOT_ACCESS_TOKEN=your_token
```

说明：

|配置项|作用|
| --- |--|
|DRIVER|NoneBot 驱动|
|HOST|Bot 监听地址|
|PORT|Bot 监听端口|
|COMMAND_START|指令前缀|
|SUPERUSERS	Bot|管理员 QQ|
|ONEBOT_ACCESS_TOKEN|OneBot Token|

---

### 配置 Minecraft

将 config_example.toml 重命名为: config.toml，并按需填写

---

### 启动 Bot

在Terminal的项目文件夹下输入:
```commandline
python bot.py
```

当控制台出现类似输出时，即表示启动成功：

```commandline
Application startup complete.
WebSocket Connection from NapCat accepted.
```

---

## 指令列表

如果修改了 COMMAND_START，请将前缀替换为对应字符。

### 基础功能

|指令|功能|
|--|--|
|`help`|查看帮助信息|
|`echo`|测试 Bot 是否在线|
|`ping`|查看网络与处理延迟|
|`status`|查看系统状态|
|`ipv6`|查看当前 IPv6 地址|

### Minecraft

| 指令 | 功能 |
| --- | --- |
| `mcinfo` | 查看服务器状态 |
| `run_server` | 启动 Minecraft 服务器 |
| `stop_server` | 停止 Minecraft 服务器 |

其中服务器启停功能仅管理员可使用。

### Todo

| 指令 | 功能 |
| --- | --- |
| `todo add` | 添加任务 |
| `todo list` | 查看任务 |
| `todo done` | 完成任务 |
| `todo revert` | 撤销上一次操作 |
| `todo branch` | 管理任务分区 |

### DDL

| 指令 | 功能 |
| --- | --- |
| `ddl add` | 添加截止任务 |
| `ddl list` | 查看截止任务 |
| `ddl del` | 删除截止任务 |

⸻

## 数据存储

运行过程中生成的数据位于：

```text
data/
├─ todo/
├─ deadlines/
├─ ip/
└─ help/
```

⸻

## 项目结构

```text
QQBot/
├─ bot.py
├─ plugins/
├─ mcserver/
├─ core/
├─ utils/
├─ data/
├─ config.toml
└─ .env
```

 其中：

* plugins：Bot 指令插件；
* mcserver：Minecraft 联动功能；
* core：核心配置与底层实现；
* utils：辅助工具；
* data：运行时数据。

---

## 常见问题

### 无法连接 NapCat（403）

请检查：

* WebSocket 地址是否正确；
* Token 是否一致；
* NapCat 是否开启 OneBot v11。

---

### 无法获取 Minecraft 状态

请确认：

* Minecraft 服务器已启动；
* 端口配置正确；
* 防火墙允许访问；
* RCON 已开启。

---

### Bot 无法撤回消息

QQ 私聊通常不支持 Bot 撤回消息。

群聊环境下可正常使用撤回功能。

---

### macOS 无法启动 Minecraft

请检查：

* config.toml 中的启动命令；
* Java 是否已安装；
* Terminal 权限是否允许自动化控制。

---

## License

MIT © 2026 Caerulues