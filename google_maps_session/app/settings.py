"""Read saved HA options without exposing account details in logs."""
import json
from pathlib import Path


def valid_email(value):
    if not isinstance(value, str):
        return False
    value = value.strip()
    return (value.count("@") == 1 and all(value.split("@"))
            and not any(char.isspace() for char in value))


def read_options(path=Path("/data/options.json")):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    email = data.get("email", "")
    return {"email": email.strip() if isinstance(email, str) else "",
            "sync_interval": max(300, min(86400, int(data.get("sync_interval", 300)))),
            "refresh_minutes": max(0, min(1440, int(data.get("refresh_minutes", 30))))}
