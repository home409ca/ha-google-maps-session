"""Ingress panel and cookie synchronization. No browser automation at login."""
import asyncio
import json
import os
from pathlib import Path
import time
from urllib.parse import urlparse

from aiohttp import ClientSession, ClientTimeout, web
from cookies import atomic_write, fingerprint, netscape
from settings import read_options, valid_email

EXPORT = Path("/share/google_maps_session/cookies.txt")


class SessionManager:
    def __init__(self, client, options, options_path=None):
        self.client = client
        self.options = options
        self.options_path = options_path
        self.lock = asyncio.Lock()
        self.last_hash = None
        self.last_validation = 0
        self.last_refresh = time.monotonic()
        self.last_notification = None
        self.status = {"state": "starting", "message": "Oczekiwanie na przeglądarkę…",
                       "last_success": None, "email": options["email"]}

    async def ha(self, service, payload):
        async with self.client.post(
            "http://supervisor/core/api/services/" + service,
            headers={"Authorization": "Bearer " + os.environ["SUPERVISOR_TOKEN"]},
            json=payload, timeout=ClientTimeout(total=240),
        ) as response:
            # Do not include the response text: errors can contain session data.
            if response.status != 200:
                raise RuntimeError("HA service failed")

    async def cdp(self, url, method):
        async with self.client.ws_connect(url, max_msg_size=4 * 1024 * 1024) as ws:
            await ws.send_json({"id": 1, "method": method})
            async with asyncio.timeout(20):
                async for msg in ws:
                    if msg.type == web.WSMsgType.TEXT:
                        data = json.loads(msg.data)
                        if data.get("id") == 1:
                            if "error" in data:
                                raise RuntimeError("Browser command failed")
                            return data.get("result", {})
            raise RuntimeError("Browser disconnected")

    async def browser_json(self, path):
        async with self.client.get("http://127.0.0.1:9222" + path) as response:
            response.raise_for_status()
            return await response.json()

    async def notify(self, message):
        if self.last_notification == message:
            return
        try:
            await self.ha("persistent_notification/create", {
                "notification_id": "google_maps_session", "title": "Sesja Google Maps",
                "message": message,
            })
            self.last_notification = message
        except Exception:
            pass

    async def sync(self, force=False):
        async with self.lock:
            try:
                if self.options_path is not None:
                    updated = await asyncio.to_thread(read_options, self.options_path)
                    if updated["email"] != self.options["email"]:
                        self.last_hash = None
                    self.options = updated
                    self.status["email"] = updated["email"]
                if not valid_email(self.options.get("email")):
                    self.status.update(state="configuration_required", message="Ustaw adres email w zakładce Konfiguracja dodatku i kliknij Zapisz. Następnie naciśnij Przekaż sesję teraz. Przeglądarka działa niezależnie od tego ustawienia.")
                    return self.status
                version = await self.browser_json("/json/version")
                data = await self.cdp(version["webSocketDebuggerUrl"], "Storage.getCookies")
                content = netscape(data["cookies"])
                digest = fingerprint(content)
                if force or digest != self.last_hash or time.monotonic() - self.last_validation >= 3600:
                    await asyncio.to_thread(atomic_write, EXPORT, content)
                    await self.ha("google_maps_session_bridge/sync", {"email": self.options["email"]})
                    self.last_hash = digest
                    self.last_validation = time.monotonic()
                    self.status["last_success"] = int(time.time())
                self.status.update(state="ok", message="Sesja przekazana do integracji Google Maps.")
                if self.last_notification is not None:
                    try:
                        await self.ha("persistent_notification/dismiss", {
                            "notification_id": "google_maps_session"})
                        self.last_notification = None
                    except Exception:
                        pass
            except ValueError:
                self.status.update(state="login_required", message="Zaloguj się w oknie poniżej. Użyj wyłącznie konta podanego w konfiguracji dodatku.")
                await self.notify("Zaloguj się do Google w panelu dodatku Sesja Google Maps.")
            except Exception:
                self.status.update(state="error", message="Nie udało się przekazać sesji. Sprawdź instalację modułu łączącego, konto i połączenie. Spróbuj ponownie; szczegóły w instrukcji.")
                await self.notify("Dodatek nie może zsynchronizować sesji. Otwórz panel Sesja Google Maps i sprawdź instrukcję instalacji lub ponownie zaloguj konto.")
            return self.status

    async def refresh_maps(self):
        minutes = self.options.get("refresh_minutes", 30)
        if not minutes or time.monotonic() - self.last_refresh < minutes * 60:
            return
        self.last_refresh = time.monotonic()
        # Never refresh Google login/challenge pages while the user is signing in.
        for page in await self.browser_json("/json/list"):
            parsed = urlparse(page.get("url", ""))
            if page.get("type") == "page" and parsed.hostname == "www.google.com" and parsed.path.startswith("/maps"):
                await self.cdp(page["webSocketDebuggerUrl"], "Page.reload")
                break


async def background(app):
    async def work():
        await asyncio.sleep(10)
        while True:
            await app["manager"].sync()
            try:
                await app["manager"].refresh_maps()
            except Exception:
                pass
            await asyncio.sleep(app["manager"].options["sync_interval"])
    task = asyncio.create_task(work())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def resources(app):
    async with ClientSession(timeout=ClientTimeout(total=30)) as client:
        options = read_options()
        app["manager"] = SessionManager(client, options, Path("/data/options.json"))
        yield


async def index(request):
    return web.FileResponse("/app/index.html", headers={"Cache-Control": "no-store"})


async def status(request):
    return web.json_response(request.app["manager"].status, headers={"Cache-Control": "no-store"})


async def desktop_diagnostics(client):
    result = {}
    writer = None
    try:
        async with asyncio.timeout(5):
            reader, writer = await asyncio.open_connection("127.0.0.1", 5900)
            result["VNC"] = "Port otwarty, brak powitania RFB"
            result["VNC"] = "OK" if (await reader.readexactly(12)).startswith(b"RFB ") else "Nieprawidłowa odpowiedź"
    except Exception:
        result.setdefault("VNC", "Brak połączenia TCP")
    finally:
        if writer is not None:
            writer.close()
            await writer.wait_closed()
    try:
        async with client.ws_connect("http://127.0.0.1:6080/websockify", protocols=["binary"]) as ws:
            result["WebSocket"] = "Połączenie otwarte, brak danych VNC"
            async with asyncio.timeout(5):
                message = await ws.receive()
                result["WebSocket"] = "OK" if message.type == web.WSMsgType.BINARY and message.data.startswith(b"RFB ") else "Brak odpowiedzi VNC"
    except Exception:
        result.setdefault("WebSocket", "Brak połączenia WebSocket")
    try:
        async with client.get("http://127.0.0.1:9222/json/version") as response:
            result["Chromium"] = "OK" if response.status == 200 else "Błąd"
    except Exception:
        result["Chromium"] = "Brak połączenia"
    print("Desktop diagnostics: " + ", ".join(f"{key}={value}" for key, value in result.items()), flush=True)
    return result


async def diagnostics(request):
    return web.json_response(await desktop_diagnostics(request.app["manager"].client),
                             headers={"Cache-Control": "no-store"})


async def sync(request):
    if request.content_type != "application/json" or request.headers.get("X-Requested-With") != "GoogleMapsSession":
        raise web.HTTPForbidden()
    return web.json_response(await request.app["manager"].sync(force=True))


if __name__ == "__main__":
    app = web.Application(client_max_size=1024)
    app.cleanup_ctx.extend([resources, background])
    app.add_routes([web.get("/", index), web.get("/status", status), web.get("/diagnostics", diagnostics), web.post("/sync", sync)])
    web.run_app(app, host="127.0.0.1", port=8098, access_log=None)
