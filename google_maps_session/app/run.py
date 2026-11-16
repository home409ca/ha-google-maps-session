"""Launch an isolated, persistent browser desktop and session worker."""
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time
from settings import read_options, valid_email

os.umask(0o077)


def main():
    options = read_options()
    if not valid_email(options["email"]):
        print("Google Maps Session: email setting is empty or invalid; desktop will start. Save email in add-on Configuration.", flush=True)
    else:
        print("Google Maps Session: saved email setting accepted; starting desktop.", flush=True)
    profile = Path("/data/profile")
    profile.mkdir(exist_ok=True)
    os.chmod("/data", 0o711)
    os.chown(profile, 1000, 1000)
    # A recreated container has a different hostname; remove stale browser locks.
    for name in ("SingletonLock", "SingletonCookie", "SingletonSocket"):
        (profile / name).unlink(missing_ok=True)
    bridge = Path("/homeassistant/custom_components/google_maps_session_bridge")
    bridge.mkdir(parents=True, exist_ok=True)
    # Update only our own files, never google_maps or HA's .storage.
    for source in Path("/bridge").rglob("*"):
        if source.is_file():
            dest = bridge / source.relative_to("/bridge")
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, dest.with_suffix(dest.suffix + ".new"))
            os.chmod(dest.with_suffix(dest.suffix + ".new"), 0o644)
            os.replace(dest.with_suffix(dest.suffix + ".new"), dest)
    # Local IPC only. The debugging port and VNC are never published.
    commands = [
        ["Xvfb", ":0", "-screen", "0", "1280x850x24", "-nolisten", "tcp", "-ac"],
        ["x11vnc", "-display", ":0", "-localhost", "-rfbport", "5900", "-forever",
         "-shared", "-nopw", "-quiet"],
        ["websockify", "--web=/usr/share/novnc", "127.0.0.1:6080", "127.0.0.1:5900"],
        ["runuser", "-u", "browser", "--", "chromium", "--no-sandbox",
         "--disable-dev-shm-usage", "--no-first-run", "--no-default-browser-check",
         "--password-store=basic", "--user-data-dir=/data/profile",
         "--remote-debugging-address=127.0.0.1", "--remote-debugging-port=9222",
         "--start-maximized", "https://www.google.com/maps"],
        ["/opt/venv/bin/python", "/app/server.py"],
        ["nginx", "-g", "daemon off;"],
    ]
    processes = []
    stopping = False

    def stop(*_):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    try:
        for command in commands:
            # Browser/VNC output may contain private URLs: do not send it to HA logs.
            processes.append(subprocess.Popen(command, start_new_session=True,
                                               stdout=subprocess.DEVNULL,
                                               stderr=subprocess.DEVNULL))
            time.sleep(0.8)
        while not stopping:
            for command, process in zip(commands, processes):
                if process.poll() is not None:
                    raise RuntimeError(f"Desktop service {command[0]} stopped (exit {process.returncode}); restart the add-on")
            time.sleep(1)
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
        deadline = time.monotonic() + 8
        for process in processes:
            try:
                process.wait(timeout=max(0.1, deadline - time.monotonic()))
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)


if __name__ == "__main__":
    main()
