import json, time, uuid


def enc(x):
    return json.dumps(x, ensure_ascii=False, separators=(",", ":"))


def dec(x):
    if isinstance(x, bytes):
        x = x.decode()
    y = json.loads(x)
    if not isinstance(y, dict):
        raise ValueError("JSON object required")
    return y


def request(action, data=None):
    return {
        "type": "request",
        "action": action,
        "request_id": str(uuid.uuid4()),
        "timestamp": int(time.time()),
        "data": data or {},
    }


def command(action, data=None):
    return {
        "type": "command",
        "action": action,
        "request_id": str(uuid.uuid4()),
        "timestamp": int(time.time()),
        "data": data or {},
    }
