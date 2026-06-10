"""Config flow: pick a SwitchBot lock already set up in the core integration."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries

from .const import DOMAIN


class QuickKeyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        locks: dict[str, str] = {}
        for entry in self.hass.config_entries.async_entries("switchbot"):
            data = entry.data
            address = data.get("address")
            sensor_type = str(data.get("sensor_type", ""))
            if address and sensor_type.startswith("lock") and data.get("encryption_key"):
                locks[address.upper()] = f"{entry.title} ({address})"

        if not locks:
            return self.async_abort(reason="no_locks")

        if user_input is not None:
            address = user_input["address"]
            await self.async_set_unique_id(address)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=f"Quick Key — {locks[address]}", data={"address": address}
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required("address"): vol.In(locks)}),
        )
