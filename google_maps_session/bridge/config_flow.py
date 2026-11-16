"""Single-instance bridge configuration."""
from homeassistant import config_entries


class BridgeConfigFlow(config_entries.ConfigFlow, domain="google_maps_session_bridge"):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        await self.async_set_unique_id("google_maps_session_bridge")
        self._abort_if_unique_id_configured()
        if user_input is not None:
            return self.async_create_entry(title="Google Maps Session Bridge", data={})
        return self.async_show_form(step_id="user")
