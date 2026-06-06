import socket

def get_ipv6():
    s = None

    try:
        s = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
        s.connect(("2001:4860:4860::8888", 80))
        return s.getsockname()[0]

    except Exception as e:
        return f"获取失败 - {e}"

    finally:
        if s:
            s.close()