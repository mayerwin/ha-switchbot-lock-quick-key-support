"""Quick Key enable/disable switch."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import BIT_ENABLE, DOMAIN
from .coordinator import QuickKeyCoordinator
from .entity import QuickKeyEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: QuickKeyCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([QuickKeyEnableSwitch(coordinator)])


class QuickKeyEnableSwitch(QuickKeyEntity, SwitchEntity):
    _attr_name = "Quick Key"
    _attr_icon = "mdi:gesture-tap-button"

    def __init__(self, coordinator: QuickKeyCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_quickkey_enable"

    @property
    def is_on(self) -> bool | None:
        return self._cfg.get("enabled")

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_apply(BIT_ENABLE, BIT_ENABLE)

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_apply(BIT_ENABLE, 0x00)
