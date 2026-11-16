"""Offline tests: real cookie format, transfer failures, and HA adapter sequencing."""
import asyncio
from http.cookiejar import MozillaCookieJar
import importlib.util
import json
from pathlib import Path
import sys
import socket
import threading
import tempfile
from types import SimpleNamespace, ModuleType
import unittest
from unittest.mock import AsyncMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "google_maps_session" / "app"))
from cookies import netscape, atomic_write
from server import SessionManager
from settings import valid_email, read_options
from run import wait_for_vnc, install_bridge

spec = importlib.util.spec_from_file_location("bridge_sync", ROOT / "google_maps_session/bridge/sync.py")
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


def cookie(**kwargs):
    return {"domain": ".google.com", "name": "__Secure-1PSID", "value": "TEST_ONLY",
            "expires": 4102444800, "path": "/", "secure": True, "httpOnly": True, **kwargs}


class CookieTests(unittest.TestCase):
    def test_addon_preserves_hacs_managed_bridge(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp)/"installed"
            destination.mkdir()
            (destination/"manifest.json").write_text('{"version":"9.0.0"}')
            self.assertFalse(install_bridge(ROOT/"google_maps_session/bridge", destination))
            self.assertEqual(json.loads((destination/"manifest.json").read_text())["version"], "9.0.0")

    def test_addon_can_bootstrap_missing_bridge(self):
        with tempfile.TemporaryDirectory() as temp:
            destination = Path(temp)/"installed"
            self.assertTrue(install_bridge(ROOT/"google_maps_session/bridge", destination))
            self.assertTrue((destination/"config_flow.py").is_file())
            self.assertTrue((destination/"translations/pl.json").is_file())
            self.assertEqual((destination/"manifest.json").read_bytes(), (ROOT/"google_maps_session/bridge/manifest.json").read_bytes())
    def test_startup_requires_actual_rfb_greeting(self):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            def serve():
                with listener.accept()[0] as connection:
                    connection.sendall(b"RFB 003.")
                    connection.sendall(b"008\n")
            worker = threading.Thread(target=serve, daemon=True)
            worker.start()
            try:
                self.assertTrue(wait_for_vnc(listener.getsockname()[1], timeout=1))
            finally:
                worker.join(timeout=2)

    def test_open_port_without_rfb_greeting_is_not_ready(self):
        with patch("run.socket.create_connection") as connect:
            connect.return_value.__enter__.return_value.recv.return_value = b""
            self.assertFalse(wait_for_vnc(5900, timeout=0.01))

    def test_startup_does_not_report_unavailable_port_as_ready(self):
        with patch("run.socket.create_connection", side_effect=ConnectionRefusedError):
            self.assertFalse(wait_for_vnc(5900, timeout=0.01))

    def test_email_validation(self):
        self.assertTrue(valid_email("  user@example.com  "))
        for value in (None, "", "user", "@example.com", "user@", "user @example.com", "u@a@b"):
            self.assertFalse(valid_email(value))

    def test_netscape_roundtrip_and_domain_filter(self):
        text = netscape([cookie(), cookie(domain="evilgoogle.com", value="EXCLUDE"),
                         cookie(name="SID", expires=-1), cookie(name="expired", expires=1)])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "cookies.txt"
            atomic_write(path, text)
            jar = MozillaCookieJar(str(path))
            jar.load(ignore_discard=True, ignore_expires=True)
            self.assertEqual({c.name for c in jar}, {"__Secure-1PSID", "SID"})
            self.assertNotIn("EXCLUDE", text)
            self.assertTrue(next(c for c in jar if c.name == "SID").expires == 0)

    def test_rejects_expired_missing_or_injected_auth(self):
        for values in ([], [cookie(expires=1)], [cookie(value="bad\nvalue")]):
            with self.assertRaises(ValueError):
                netscape(values)


class WorkerTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_email_keeps_panel_available_without_browser_or_ha_call(self):
        m = self.make_manager()
        m.options["email"] = ""
        await m.sync()
        self.assertEqual(m.status["state"], "configuration_required")
        m.browser_json.assert_not_called()
        m.ha.assert_not_called()

    async def test_reads_saved_email_after_start_and_retries(self):
        m = self.make_manager()
        with tempfile.TemporaryDirectory() as temp, patch("server.EXPORT", Path(temp)/"cookies.txt"):
            options = Path(temp)/"options.json"
            m.options_path = options
            options.write_text(json.dumps({"email": ""}))
            await m.sync()
            self.assertEqual(m.status["state"], "configuration_required")
            options.write_text(json.dumps({"email": "  saved@example.com  "}))
            await m.sync()
            self.assertEqual(m.status["state"], "ok")
            m.ha.assert_awaited_with("google_maps_session_bridge/sync", {"email": "saved@example.com"})

    def make_manager(self):
        m = SessionManager(None, {"email": "test@example.com", "refresh_minutes": 30})
        m.browser_json = AsyncMock(return_value={"webSocketDebuggerUrl": "ws://localhost"})
        m.cdp = AsyncMock(return_value={"cookies": [cookie()]})
        m.ha = AsyncMock()
        m.notify = AsyncMock()
        return m

    async def test_success_deduplicates_and_manual_forces(self):
        m = self.make_manager()
        with tempfile.TemporaryDirectory() as temp, patch("server.EXPORT", Path(temp)/"cookies.txt"):
            await m.sync()
            await m.sync()
            self.assertEqual(m.ha.await_count, 1)
            await m.sync(force=True)
            self.assertEqual(m.ha.await_count, 2)
            self.assertEqual(m.status["state"], "ok")

    async def test_failed_transfer_retries_identical_cookies(self):
        m = self.make_manager()
        m.ha.side_effect = [RuntimeError("private data"), None]
        with tempfile.TemporaryDirectory() as temp, patch("server.EXPORT", Path(temp)/"cookies.txt"):
            await m.sync()
            self.assertEqual(m.status["state"], "error")
            self.assertNotIn("private data", m.status["message"])
            self.assertIsNone(m.last_hash)
            await m.sync()
            self.assertEqual(m.status["state"], "ok")

    async def test_invalid_session_does_not_replace_export(self):
        m = self.make_manager()
        m.cdp.return_value = {"cookies": []}
        with tempfile.TemporaryDirectory() as temp, patch("server.EXPORT", Path(temp)/"cookies.txt"):
            await m.sync()
            self.assertEqual(m.status["state"], "login_required")
            self.assertFalse((Path(temp)/"cookies.txt").exists())
            m.ha.assert_not_called()

    async def test_never_refresh_login_page(self):
        m = self.make_manager()
        m.last_refresh = 0
        m.browser_json.return_value = [{"type": "page", "url": "https://accounts.google.com/signin",
                                       "webSocketDebuggerUrl": "ws://localhost"}]
        await m.refresh_maps()
        m.cdp.assert_not_called()


class BridgeTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)
        self.entry = SimpleNamespace(unique_id="test@example.com", version=3,
                                     disabled_by=None, data={"cookies_file": "old"}, entry_id="one")
        self.api = SimpleNamespace(load_cookies=lambda _: None, get_new_data=lambda: None,
                                   save_cookies=lambda p: Path(p).write_text("TEST_COOKIE"),
                                   close=lambda: None)
        self.fake = {}
        for name in ("config_flow", "gm_loc_sharing", "helpers"):
            self.fake["custom_components.google_maps."+name] = ModuleType(name)
        self.fake["custom_components.google_maps.config_flow"].GoogleMapsConfigFlow = SimpleNamespace(VERSION=3)
        self.fake["custom_components.google_maps.gm_loc_sharing"].GMLocSharing = lambda _: self.api
        helpers = self.fake["custom_components.google_maps.helpers"]
        helpers.cookies_file_path = lambda h, name: self.path / name
        helpers.old_cookies_file_path = lambda h, email: self.path / "legacy"
        self.export = self.path / "export"
        self.export.write_text("TEST")
        self.events = []

        async def executor(func, *args):
            return func(*args)

        def update(entry, **kwargs):
            self.events.append("update")
            entry.data = kwargs["data"]

        async def reload(entry_id):
            self.events.append("reload")
            self.assertNotEqual(self.entry.data["cookies_file"], "old")
            self.assertEqual((self.path/self.entry.data["cookies_file"]).read_text(), "TEST_COOKIE")
            return True

        self.flow = SimpleNamespace(async_progress=lambda: [], async_abort=lambda _: None)
        self.entries = SimpleNamespace(async_entries=lambda _: [self.entry], async_update_entry=update,
                                       async_reload=reload, flow=self.flow)
        self.hass = SimpleNamespace(config_entries=self.entries, async_add_executor_job=executor)
        self.modules = patch.dict(sys.modules, self.fake)
        self.modules.start()
        self.export_patch = patch.object(bridge, "EXPORT", self.export)
        self.export_patch.start()

    def tearDown(self):
        self.modules.stop()
        self.export_patch.stop()
        self.temp.cleanup()

    async def test_existing_session_uses_new_file_before_reload(self):
        await bridge.synchronize(self.hass, "test@example.com")
        self.assertEqual(self.events, ["update", "reload"])

    async def test_rejected_session_does_not_touch_entry(self):
        def reject():
            raise ValueError("Rejected")
        self.api.get_new_data = reject
        with self.assertRaises(ValueError):
            await bridge.synchronize(self.hass, "test@example.com")
        self.assertEqual(self.events, [])
        self.assertEqual(self.entry.data["cookies_file"], "old")

    async def test_create_account_follows_flow_and_removes_staged_file(self):
        steps = ["username", "get_cookies", "account_entity", "max_gps_accuracy", "update_period"]
        self.entries.async_entries = lambda _: []
        result = lambda step: {"type": "form", "step_id": step, "flow_id": "flow"}
        self.flow.async_init = AsyncMock(return_value=result(steps[0]))
        self.flow.async_configure = AsyncMock(side_effect=[result(s) for s in steps[1:]] + [{"type": "create_entry"}])
        await bridge.synchronize(self.hass, "test@example.com")
        self.assertEqual(self.flow.async_configure.await_count, 5)
        self.assertFalse((self.path/"legacy").exists())

    async def test_changed_flow_fails_and_restores_legacy_file(self):
        self.entries.async_entries = lambda _: []
        legacy = self.path/"legacy"
        legacy.write_bytes(b"PREVIOUS")
        self.flow.async_init = AsyncMock(return_value={"type": "form", "step_id": "unknown", "flow_id": "flow"})
        self.flow.async_abort = unittest.mock.Mock()
        with self.assertRaises(RuntimeError):
            await bridge.synchronize(self.hass, "test@example.com")
        self.assertEqual(legacy.read_bytes(), b"PREVIOUS")
        self.flow.async_abort.assert_called_once_with("flow")


if __name__ == "__main__":
    unittest.main()
