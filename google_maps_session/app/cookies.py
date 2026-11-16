"""Cookie conversion; never log credential values."""
import hashlib
import os
import time
from pathlib import Path

AUTH_NAMES = {"__Secure-1PSID", "__Secure-3PSID"}


def netscape(cookies, now=None):
    now = time.time() if now is None else now
    rows = []
    authenticated = False
    for cookie in cookies:
        domain = cookie["domain"]
        # Deliberately limit the export to google.com, used by upstream.
        if domain.lstrip(".") != "google.com" and not domain.endswith(".google.com"):
            continue
        expires = cookie.get("expires", -1)
        if expires > 0 and expires <= now:
            continue
        values = [domain, "TRUE" if domain.startswith(".") else "FALSE",
                  cookie.get("path", "/"), "TRUE" if cookie.get("secure") else "FALSE",
                  str(int(expires)) if expires > 0 else "0", cookie["name"], cookie["value"]]
        if any(any(c in value for c in "\t\r\n") for value in values):
            raise ValueError("Invalid cookie field")
        if cookie.get("httpOnly"):
            values[0] = "#HttpOnly_" + values[0]
        rows.append("\t".join(values))
        authenticated |= cookie["name"] in AUTH_NAMES and expires > now
    if not authenticated:
        raise ValueError("Login required")
    return "# Netscape HTTP Cookie File\n" + "\n".join(sorted(rows)) + "\n"


def fingerprint(content):
    return hashlib.sha256(content.encode()).hexdigest()


def atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_suffix(".tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)
