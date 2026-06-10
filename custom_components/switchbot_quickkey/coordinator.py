"""Quick Key coordinator for the SwitchBot Lock Ultra.

Reuses the *live* SwitchbotLock object owned by the core `switchbot` integration
(`entry.runtime_data.device`) so our reads/writes ride its existing BLE
connection and operation-lock — serialized with HA's own polls. Opening our own
second connection caused permanent org.bluez.Error.InProgress contention for the
lock's single radio; reuse eliminates it entirely (and the keys come for free).
"""
from __future__ import annotations

import asyncio
import logging
import time

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from switchbot.devices.lock import SwitchbotLock

from .const import (
    BIT_DOUBLE,
    BIT_ENABLE,
    CMD_READ,
    CONFIRM_READ_DEADLINE_S,
    DOMAIN,
    MASK_FUNCTION,
    READ_DEADLINE_S,
    RETRY_BACKOFF_S,
    WRITE_DEADLINE_S,
)

_LOGGER = logging.getLogger(__name__)

# Every valid Quick Key config byte has bits 6-7 set (0xC0 status flags).
VALID_HIGH_BITS = 0xC0


def _is_valid(cfg: int | None) -> bool:
    return cfg is not None and (cfg & VALID_HIGH_BITS) == VALID_HIGH_BITS


async def _read_once(dev: SwitchbotLock) -> int | None:
    res = await dev._send_command(CMD_READ)
    if not res or len(res) < 2 or res[0] not in (1, 6):
        return None
    return res[1]


async def read_config(dev: SwitchbotLock, deadline: float = READ_DEADLINE_S) -> int | None:
    """Read the config byte; retry up to `deadline`s, require a valid byte
    (prefer two agreeing reads). None if it never reads cleanly."""
    end = time.monotonic() + deadline
    last: int | None = None
    while True:
        try:
            cfg = await _read_once(dev)
        except Exception as ex:  # noqa: BLE001
            _LOGGER.debug("Quick Key read attempt failed: %s", ex)
            cfg = None
        if _is_valid(cfg):
            if cfg == last:
                return cfg
            last = cfg
        if time.monotonic() >= end:
            return last
        await asyncio.sleep(RETRY_BACKOFF_S)


async def write_config(dev: SwitchbotLock, mask: int, value: int,
                       deadline: float = WRITE_DEADLINE_S) -> int | None:
    """Masked-write; retry up to `deadline`s until the lock echoes a valid byte
    carrying the requested bits. Returns the new byte, or None."""
    cmd = f"570f4e040100{mask:02x}{value:02x}ff"
    end = time.monotonic() + deadline
    while True:
        try:
            res = await dev._send_command(cmd)
        except Exception as ex:  # noqa: BLE001
            _LOGGER.debug("Quick Key write attempt failed: %s", ex)
            res = None
        echo = res[1] if res and len(res) >= 2 and res[0] in (1, 6) else None
        if _is_valid(echo) and (echo & mask) == (value & mask):
            return echo
        if time.monotonic() >= end:
            return None
        await asyncio.sleep(RETRY_BACKOFF_S)


def parse_config(cfg: int | None) -> dict:
    if cfg is None:
        return {"raw": None, "enabled": None, "double_press": None, "function": None}
    return {
        "raw": cfg,
        "enabled": bool(cfg & BIT_ENABLE),
        "double_press": bool(cfg & BIT_DOUBLE),
        "function": cfg & MASK_FUNCTION,
    }


class QuickKeyCoordinator(DataUpdateCoordinator[dict]):
    """On-demand coordinator (no periodic polling) reusing the core device."""

    def __init__(self, hass: HomeAssistant, address: str) -> None:
        super().__init__(hass, _LOGGER, name=f"{DOMAIN} {address}", update_interval=None)
        self.address = address.upper()

    def core_device(self) -> SwitchbotLock | None:
        """The live SwitchbotLock owned by the core `switchbot` integration."""
        for entry in self.hass.config_entries.async_entries("switchbot"):
            if str(entry.data.get("address", "")).upper() == self.address:
                coordinator = getattr(entry, "runtime_data", None)
                device = getattr(coordinator, "device", None)
                if isinstance(device, SwitchbotLock):
                    return device
        return None

    async def _async_update_data(self) -> dict:
        dev = self.core_device()
        if dev is None:
            return parse_config(None)
        val = await read_config(dev)
        return parse_config(val)

    async def async_apply(self, mask: int, value: int) -> None:
        dev = self.core_device()
        if dev is None:
            raise HomeAssistantError(
                f"Core SwitchBot device for {self.address} is not available"
            )
        echo = await write_config(dev, mask, value)
        cfg = await read_config(dev, deadline=CONFIRM_READ_DEADLINE_S)
        if cfg is None:
            cfg = echo
        self.async_set_updated_data(parse_config(cfg))
        if echo is None:
            raise HomeAssistantError(
                "Quick Key write was not confirmed by the lock; state refreshed from read-back"
            )
