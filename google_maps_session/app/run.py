"""Launch an isolated, persistent browser desktop and session worker."""
import os
from pathlib import Path
import shutil
import signal
import socket
import subprocess
import time
from settings import read_options, valid_email

def wait_for_port(port, timeout=20):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return True
        except OSError:
            time.sleep(0.2)
    return False


def main():
    os.umask(0o077)
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
        ["x11vnc", "-display", ":0", "-listen", "127.0.0.1", "-no6",
         "-rfbport", "5900", "-forever", "-shared", "-nopw", "-noshm", "-noxdamage"],
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
            # Keep browser URLs private; expose server diagnostics, not Chromium output.
            visible = command[0] in ("Xvfb", "x11vnc", "websockify", "nginx") or command[0] == "/opt/venv/bin/python"
            processes.append(subprocess.Popen(command, start_new_session=True,
                                               stdout=None if visible else subprocess.DEVNULL,
                                               stderr=None if visible else subprocess.DEVNULL))
            time.sleep(0.8)
            if command[0] == "Xvfb":
                deadline = time.monotonic() + 10
                while not Path("/tmp/.X11-unix/X0").exists() and time.monotonic() < deadline:
                    time.sleep(0.2)
            elif command[0] == "x11vnc":
                ready = wait_for_port(5900)
                print("Desktop startup: VNC " + ("listening on local port 5900" if ready else "NOT listening on local port 5900; inspect x11vnc output above"), flush=True)
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
