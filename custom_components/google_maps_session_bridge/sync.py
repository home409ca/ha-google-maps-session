"""Adapter for pnbruckner/ha-google-maps config flow v3 (integration 2.1.0)."""
import os
from pathlib import Path
from uuid import uuid4

EXPORT = Path("/share/google_maps_session/cookies.txt")


class SessionTransferError(RuntimeError):
    """A fixed, safe explanation; never includes cookie values or response data."""

    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


async def advance(hass, result, step, values):
    if result.get("type") not in ("form", "menu") or result.get("step_id") != step or result.get("errors"):
        raise RuntimeError("Unsupported Google Maps configuration step")
    return await hass.config_entries.flow.async_configure(result["flow_id"], values)


async def create_account(hass, email, api, legacy_path):
    """Use upstream's normal flow, including upstream cookie validation and saving."""
    result = None

    def stage():
        previous = legacy_path.read_bytes() if legacy_path.exists() else None
        api.save_cookies(str(legacy_path))
        os.chmod(legacy_path, 0o600)
        return previous

    previous = await hass.async_add_executor_job(stage)
    try:
        result = await hass.config_entries.flow.async_init("google_maps", context={"source": "user"})
        result = await advance(hass, result, "username", {"username": email})
        result = await advance(hass, result, "get_cookies", {"use_existing_cookies": True})
        result = await advance(hass, result, "account_entity", {"create_acct_entity": False})
        result = await advance(hass, result, "max_gps_accuracy", {"max_gps_accuracy": 1000})
        result = await advance(hass, result, "update_period", {"scan_interval": {"seconds": 60}})
        if result.get("type") != "create_entry":
            raise RuntimeError("Google Maps account was not created")
    finally:
        if result and result.get("type") in ("form", "menu"):
            hass.config_entries.flow.async_abort(result["flow_id"])

        def restore():
            if previous is None:
                legacy_path.unlink(missing_ok=True)
            else:
                legacy_path.write_bytes(previous)
        await hass.async_add_executor_job(restore)


async def synchronize(hass, email):
    # Import only after HA has loaded the dependency. Fail closed on built-in or
    # incompatible variants instead of guessing their credential layout.
    from custom_components.google_maps.config_flow import GoogleMapsConfigFlow
    from custom_components.google_maps.gm_loc_sharing import GMLocSharing, InvalidCookies
    from custom_components.google_maps.helpers import cookies_file_path, old_cookies_file_path

    if GoogleMapsConfigFlow.VERSION != 3 or "@" not in email or any(c in email for c in "\r\n\t"):
        raise ValueError("Unsupported integration or invalid email")
    matches = [e for e in hass.config_entries.async_entries("google_maps")
               if (e.unique_id or "").casefold() == email.casefold()]
    if len(matches) > 1 or (matches and (matches[0].version != 3 or matches[0].disabled_by)):
        raise ValueError("Duplicate, disabled or unsupported Google Maps account")

    def validate():
        if not EXPORT.is_file():
            raise SessionTransferError("export_missing", "Brak pliku sesji z dodatku. Otwórz panel Google Maps Session i kliknij Przekaż sesję teraz, aby zapisać aktualne ciasteczka.")
        if EXPORT.is_symlink() or EXPORT.stat().st_size > 1024 * 1024:
            raise ValueError("Invalid cookie export")
        api = GMLocSharing(email)
        phase = "load"
        try:
            api.load_cookies(str(EXPORT))
            phase = "google"
            api.get_new_data()
        except InvalidCookies:
            api.close()
            if phase == "load":
                raise SessionTransferError("auth_cookie_missing", "W zapisanym pliku brakuje ważnego ciasteczka __Secure-1PSID lub __Secure-3PSID. Otwórz Mapy Google w przeglądarce dodatku, sprawdź logowanie właściwego konta i ponownie kliknij Przekaż sesję teraz.") from None
            raise SessionTransferError("google_rejected_session", "Wymagane ciasteczka zostały wczytane, ale Google odrzucił sesję przy zapytaniu o lokalizacje. W przeglądarce dodatku otwórz Mapy Google i Udostępnianie lokalizacji, dokończ ewentualne potwierdzenia Google, a następnie kliknij Przekaż sesję teraz. Dotychczasowego konta integracji nie zmieniono.") from None
        except Exception:
            api.close()
            raise
        return api

    api = await hass.async_add_executor_job(validate)
    try:
        if not matches:
            await create_account(hass, email, api, old_cookies_file_path(hass, email))
            return

        entry = matches[0]
        name = uuid4().hex
        path = cookies_file_path(hass, name)

        def save():
            path.parent.mkdir(parents=True, exist_ok=True)
            api.save_cookies(str(path))
            os.chmod(path, 0o600)

        # Save to a NEW filename so upstream shutdown never overwrites this session
        # with cookies still held in memory. Upstream removes its old file on unload.
        await hass.async_add_executor_job(save)
        hass.config_entries.async_update_entry(entry, data={**entry.data, "cookies_file": name})
        if not await hass.config_entries.async_reload(entry.entry_id):
            raise RuntimeError("Google Maps reload failed; new cookies retained for retry")
        for flow in hass.config_entries.flow.async_progress():
            context = flow.get("context", {})
            if (flow.get("handler") == "google_maps" and context.get("entry_id") == entry.entry_id
                    and context.get("source") == "reauth"):
                hass.config_entries.flow.async_abort(flow["flow_id"])
    finally:
        await hass.async_add_executor_job(api.close)
