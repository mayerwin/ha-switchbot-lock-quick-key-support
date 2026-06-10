"""SwitchBot Lock Quick Key (interim custom component).

Reuses the core `switchbot` integration's live device object (connection + keys),
so there is nothing to configure beyond picking the lock and no second BLE
connection is opened. No periodic polling — state refreshes only on interaction,
the Refresh button, and once at startup as soon as Bluetooth has seen the lock.
"""
from __future__ import annotations

from homeassistant.components import bluetooth
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady

from .const import DOMAIN
from .coordinator import QuickKeyCoordinator

PLATFORMS = [Platform.SWITCH, Platform.SELECT, Platform.SENSOR, Platform.BUTTON]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    address = entry.data["address"].upper()
    coordinator = QuickKeyCoordinator(hass, address)

    # We ride on the core switchbot integration's device; if it hasn't loaded
    # yet, retry setup later.
    if coordinator.core_device() is None:
        raise ConfigEntryNotReady(
            f"Core SwitchBot device for {address} not loaded yet"
        )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # One read at startup, once Bluetooth has actually seen the lock.
    def _schedule_initial_refresh() -> None:
        entry.async_create_background_task(
            hass, coordinator.async_refresh(), "switchbot_quickkey_initial_refresh"
        )

    if bluetooth.async_ble_device_from_address(hass, address, connectable=True) is not None:
        _schedule_initial_refresh()
    else:
        cancels: list = []

        @callback
        def _on_first_seen(service_info, change) -> None:
            for cancel in cancels:
                cancel()
            cancels.clear()
            _schedule_initial_refresh()

        cancels.append(
            bluetooth.async_register_callback(
                hass,
                _on_first_seen,
                {"address": address, "connectable": True},
                bluetooth.BluetoothScanningMode.ACTIVE,
            )
        )
        entry.async_on_unload(lambda: [cancel() for cancel in cancels])

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unloaded
