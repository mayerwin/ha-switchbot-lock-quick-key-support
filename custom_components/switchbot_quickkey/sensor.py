"""Diagnostic sensor exposing the raw Quick Key config byte (handy for validation)."""
from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import QuickKeyCoordinator
from .entity import QuickKeyEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: QuickKeyCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([QuickKeyRawSensor(coordinator)])


class QuickKeyRawSensor(QuickKeyEntity, SensorEntity):
    _attr_name = "Quick Key config byte"
    _attr_icon = "mdi:numeric"
    _attr_entity_category = EntityCategory.DIAGNOSTIC

    def __init__(self, coordinator: QuickKeyCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_quickkey_raw"

    @property
    def native_value(self) -> str | None:
        raw = self._cfg.get("raw")
        return f"0x{raw:02x}" if raw is not None else None
