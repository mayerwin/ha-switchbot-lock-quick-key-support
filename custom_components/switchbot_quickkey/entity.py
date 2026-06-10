"""Base entity for Quick Key entities."""
from __future__ import annotations

from homeassistant.helpers.device_registry import CONNECTION_BLUETOOTH, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import QuickKeyCoordinator


class QuickKeyEntity(CoordinatorEntity[QuickKeyCoordinator]):
    """Attaches to the existing SwitchBot lock device via its BT connection."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: QuickKeyCoordinator) -> None:
        super().__init__(coordinator)
        # Same connection tuple as the core SwitchBot integration -> HA merges
        # these entities onto the existing Lock Ultra device card.
        self._attr_device_info = DeviceInfo(
            connections={(CONNECTION_BLUETOOTH, coordinator.address)},
        )

    @property
    def available(self) -> bool:
        # Always "available" so an unreadable state shows as 'unknown' (None)
        # rather than 'unavailable' — never a stale/misleading value.
        return True

    @property
    def _cfg(self) -> dict:
        return self.coordinator.data or {}
