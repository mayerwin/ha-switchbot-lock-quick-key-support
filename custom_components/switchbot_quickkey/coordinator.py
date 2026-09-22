"""Quick Key coordinator for the SwitchBot Lock Ultra.

Reuses the *live* SwitchbotLock object owned by the core `switchbot` integration
(`entry.runtime_data.device`) so our reads/writes ride its existing BLE
connection and operation-lock, serialized with HA's own polls. Opening our own
second connection caused permanent org.bluez.Error.InProgress contention for the
lock's single radio; reuse eliminates it entirely (and the keys come for free).

Nothing here validates the *content* of the config byte. The reply is already
decrypted and authenticated by pySwitchbot, `_read_once` checks the status byte
and length, and `read_config` requires two agreeing reads before it accepts a
value. A "does this byte look plausible" test on top of that bought nothing and
silently broke a lock whose undecoded high bits differ from ours; see const.py.
"""
from __future__ import annotations

import asyncio
import logging
import time

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from switchbot.devices.lock import SwitchbotLock

from .const import (
    BIT_DOUBLE,
    BIT_ENABLE,
    CMD_READ,
    CONFIRM_READ_DEADLINE_S,
    DOMAIN,
    FUNCTION_LABELS,
    MASK_FUNCTION,
    READ_DEADLINE_S,
    RETRY_BACKOFF_S,
    WRITE_DEADLINE_S,
)

_LOGGER = logging.getLogger(__name__)


def _hexbyte(value: int | None) -> str:
    return "none" if value is None else f"0x{value:02x}"


async def _read_once(dev: SwitchbotLock) -> int | None:
    res = await dev._send_command(CMD_READ)
    if not res or len(res) < 2 or res[0] not in (1, 6):
        # Debug rather than warning: this runs inside a retry loop, so a genuinely
        # unreachable lock would emit ~30 of these per read. The give-up warning
        # below is the one that fires once.
        _LOGGER.debug(
            "Quick Key reply discarded: %s",
            res.hex() if res else repr(res),
        )
        return None
    _LOGGER.debug("Quick Key read reply: %s", res.hex())
    return res[1]


async def read_config(dev: SwitchbotLock, deadline: float = READ_DEADLINE_S) -> int | None:
    """Read the config byte; retry up to `deadline`s, preferring two agreeing
    reads. Returns the last byte read, or None if nothing ever read cleanly."""
    end = time.monotonic() + deadline
    last: int | None = None
    while True:
        try:
            cfg = await _read_once(dev)
        except Exception as ex:  # noqa: BLE001
            _LOGGER.debug("Quick Key read attempt failed: %s", ex)
            cfg = None
        if cfg is not None:
            if cfg == last:
                return cfg
            last = cfg
        if time.monotonic() >= end:
            if last is None:
                _LOGGER.warning(
                    "Quick Key read gave up after %.0fs: the lock never returned a "
                    "usable reply (enable debug logging for %s to see the raw replies)",
                    deadline,
                    __package__,
                )
            else:
                _LOGGER.warning(
                    "Quick Key read gave up after %.0fs without two agreeing reads; "
                    "using the last byte seen (%s)",
                    deadline,
                    _hexbyte(last),
                )
            return last
        await asyncio.sleep(RETRY_BACKOFF_S)


async def write_config(dev: SwitchbotLock, mask: int, value: int,
                       deadline: float = WRITE_DEADLINE_S) -> int | None:
    """Masked-write; retry up to `deadline`s until the lock echoes a byte
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
        if echo is not None and (echo & mask) == (value & mask):
            return echo
        if time.monotonic() >= end:
            _LOGGER.warning(
                "Quick Key write gave up after %.0fs: asked for mask=%s value=%s, "
                "last echo was %s",
                deadline,
                _hexbyte(mask),
                _hexbyte(value),
                _hexbyte(echo),
            )
            return None
        await asyncio.sleep(RETRY_BACKOFF_S)


def parse_config(cfg: int | None) -> dict:
    if cfg is None:
        return {"raw": None, "enabled": None, "double_press": None, "function": None}
    func = cfg & MASK_FUNCTION
    if func not in FUNCTION_LABELS:
        # The 2-bit function field has 4 possible values but only 3 are defined.
        # A firmware variant or a corrupted BLE byte could report the undefined 4th
        # (0b11); keep the well-defined enable/trigger bits and surface the function
        # as unknown rather than guessing or passing a stray value to the select.
        _LOGGER.warning(
            "Unknown Quick Key function value: 0x%02x (config byte 0x%02x)", func, cfg
        )
        func = None
    return {
        "raw": cfg,
        "enabled": bool(cfg & BIT_ENABLE),
        "double_press": bool(cfg & BIT_DOUBLE),
        "function": func,
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
            # Distinct from a failed BLE read: without this the two look identical
            # from outside, which is a debugging dead end.
            raise UpdateFailed(
                f"The core switchbot integration has no live device for {self.address}"
            )
        return parse_config(await read_config(dev))

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
