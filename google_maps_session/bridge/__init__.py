"""Transfer sessions through HA APIs, without editing .storage files directly."""
import asyncio
import logging

import voluptuous as vol
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.service import async_register_admin_service

from .sync import synchronize

DOMAIN = "google_maps_session_bridge"
_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry):
    lock = asyncio.Lock()

    async def handle(call):
        async with lock:
            try:
                await synchronize(hass, call.data["email"].strip())
            except Exception as err:
                # Google/requests exceptions may contain private data: log type only.
                _LOGGER.warning("Session transfer failed (%s)", type(err).__name__)
                raise HomeAssistantError(
                    "Session transfer failed. Check Google login, bridge compatibility "
                    "and the email configured in the add-on."
                ) from None

    async_register_admin_service(hass, DOMAIN, "sync", handle,
                                 schema=vol.Schema({vol.Required("email"): str}))
    return True


async def async_unload_entry(hass, entry):
    hass.services.async_remove(DOMAIN, "sync")
    return True
