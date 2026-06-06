import psutil


def has_java_process() -> bool:
    """
    检测是否存在 Minecraft 服务端 Java 进程。
    """
    for proc in psutil.process_iter(["name", "cmdline"]):
        try:
            name = proc.info.get("name") or ""
            cmdline = proc.info.get("cmdline") or []

            cmdline_text = " ".join(str(x) for x in cmdline)

            if "java" in cmdline_text or "server.jar" in cmdline_text:
                return True

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return False