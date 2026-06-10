"""Quick Key Function (3-way) and Trigger (single/double) selects."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    BIT_DOUBLE,
    DOMAIN,
    FUNCTION_LABELS,
    FUNCTION_OPTIONS,
    FUNCTION_VALUES,
    MASK_FUNCTION,
    TRIGGER_DOUBLE,
    TRIGGER_OPTIONS,
    TRIGGER_SINGLE,
)
from .coordinator import QuickKeyCoordinator
from .entity import QuickKeyEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: QuickKeyCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [QuickKeyFunctionSelect(coordinator), QuickKeyTriggerSelect(coordinator)]
    )


class QuickKeyFunctionSelect(QuickKeyEntity, SelectEntity):
    _attr_name = "Quick Key function"
    _attr_icon = "mdi:lock-smart"
    _attr_options = FUNCTION_OPTIONS

    def __init__(self, coordinator: QuickKeyCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_quickkey_function"

    @property
    def current_option(self) -> str | None:
        func = self._cfg.get("function")
        return FUNCTION_LABELS.get(func) if func is not None else None

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_apply(MASK_FUNCTION, FUNCTION_VALUES[option])


class QuickKeyTriggerSelect(QuickKeyEntity, SelectEntity):
    _attr_name = "Quick Key trigger"
    _attr_icon = "mdi:gesture-double-tap"
    _attr_options = TRIGGER_OPTIONS

    def __init__(self, coordinator: QuickKeyCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.address}_quickkey_trigger"

    @property
    def current_option(self) -> str | None:
        dbl = self._cfg.get("double_press")
        if dbl is None:
            return None
        return TRIGGER_DOUBLE if dbl else TRIGGER_SINGLE

    async def async_select_option(self, option: str) -> None:
        value = BIT_DOUBLE if option == TRIGGER_DOUBLE else 0x00
        await self.coordinator.async_apply(BIT_DOUBLE, value)
