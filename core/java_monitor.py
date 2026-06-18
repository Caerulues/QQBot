import psutil

def has_java_process() -> bool:
    for proc in psutil.process_iter(["name", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            cmdline_text = " ".join(str(x) for x in cmdline)

            if "java" in cmdline_text or "server.jar" in cmdline_text:
                return True

        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            continue

    return False