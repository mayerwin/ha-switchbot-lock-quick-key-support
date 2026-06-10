"""On-demand Refresh button (reads the lock now — no periodic polling)."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import QuickKeyCoordinator
from .entity import QuickKeyEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: QuickKeyCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([QuickKeyRefreshButton(coordinator)])


class QuickKeyRefreshButton(QuickKeyEntity, ButtonEntity):
    _attr_name = "Refresh Quick Key"
    _attr_icon = "mdi:refresh"

    def __init__(self, coordinator: QuickKeyCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_quickkey_refresh"

    async def async_press(self) -> None:
        await self.coordinator.async_refresh()
