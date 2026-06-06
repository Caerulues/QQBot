import asyncio
from typing import Optional

from core.terminal_state import (
    save_minecraft_window_id,
    load_minecraft_window_id,
    clear_minecraft_window_id,
)


from core.config import config

TERMINAL_TITLE = config.server.terminal_title


async def run_osascript(script: str) -> tuple[str, str, int]:
    proc = await asyncio.create_subprocess_exec(
        "osascript",
        "-e",
        script,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate()

    out = stdout.decode("utf-8", errors="ignore").strip()
    err = stderr.decode("utf-8", errors="ignore").strip()

    return out, err, proc.returncode


async def terminal_window_exists(window_id: int) -> bool:
    script = f'''
    tell application "Terminal"
        try
            get id of window id {window_id}
            return "true"
        on error
            return "false"
        end try
    end tell
    '''

    stdout, _, _ = await run_osascript(script)

    return stdout == "true"


async def find_minecraft_terminal_by_title() -> Optional[int]:
    script = f'''
    tell application "Terminal"
        repeat with w in windows
            try
                if custom title of w contains "{TERMINAL_TITLE}" then
                    return id of w
                end if
            end try
        end repeat

        return ""
    end tell
    '''

    stdout, _, _ = await run_osascript(script)

    if not stdout:
        return None

    try:
        return int(stdout)
    except ValueError:
        return None


async def restore_minecraft_window_id() -> Optional[int]:
    """
    优先从 data/server_terminal.json 恢复 window_id。
    如果 window_id 失效，则尝试按 Terminal 标题查找。
    """
    saved_id = load_minecraft_window_id()

    if saved_id and await terminal_window_exists(saved_id):
        return saved_id

    found_id = await find_minecraft_terminal_by_title()

    if found_id and await terminal_window_exists(found_id):
        save_minecraft_window_id(found_id)
        return found_id

    clear_minecraft_window_id()
    return None


async def open_minecraft_terminal(server_path: str, command: str) -> int:
    safe_path = server_path.replace("\\", "\\\\").replace('"', '\\"')
    safe_command = command.replace("\\", "\\\\").replace('"', '\\"')

    script = f'''
    tell application "Terminal"
        activate
        do script "printf '\\\\e]0;{TERMINAL_TITLE}\\\\a'; cd \\"{safe_path}\\" && {safe_command}"
        delay 1

        set targetWindow to front window
        set custom title of targetWindow to "{TERMINAL_TITLE}"

        return id of targetWindow
    end tell
    '''

    stdout, stderr, code = await run_osascript(script)

    if code != 0 or not stdout:
        raise RuntimeError(f"无法创建Minecraft终端窗口: {stderr or stdout}")

    window_id = int(stdout.strip())
    save_minecraft_window_id(window_id)

    return window_id


async def send_command_to_terminal(window_id: int, command: str):
    safe_command = command.replace("\\", "\\\\").replace('"', '\\"')

    script = f'''
    tell application "Terminal"
        try
            do script "{safe_command}" in selected tab of window id {window_id}
        on error errMsg
            error errMsg
        end try
    end tell
    '''

    stdout, stderr, code = await run_osascript(script)

    if code != 0:
        raise RuntimeError(f"向Terminal发送命令失败: {stderr or stdout}")


async def close_terminal_window(window_id: int):
    script = f'''
    tell application "Terminal"
        try
            close window id {window_id}
        end try
    end tell
    '''

    await run_osascript(script)


async def stop_minecraft_terminal(window_id: int, close_after_stop: bool = True):
    await send_command_to_terminal(window_id, "stop")

    if close_after_stop:
        await asyncio.sleep(5)
        await close_terminal_window(window_id)
        clear_minecraft_window_id()