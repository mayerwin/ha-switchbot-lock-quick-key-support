# SwitchBot Lock Quick Key (interim custom component)

Exposes the SwitchBot **Lock Ultra** "Quick Key" settings in Home Assistant —
which the core `switchbot` integration and SwitchBot's own cloud API do **not**.
Reverse-engineered from a decrypted BLE capture of the official app (June 2026).

## Entities (added onto the existing Lock Ultra device)

| Entity | Type | Values |
|--------|------|--------|
| `switch.*_quick_key` | switch | Quick Key enabled on/off |
| `select.*_quick_key_function` | select | Lock & Unlock / Lock Only / Unlock Only |
| `select.*_quick_key_trigger` | select | Single Press / Double Press |
| `button.*_refresh_quick_key` | button | read the lock's current state now |
| `sensor.*_quick_key_config_byte` | sensor (diag) | raw config byte, e.g. `0xc2` |

State is **confirmed by the lock**: every write retries for up to 15 s to ride
out BLE contention, then reads the byte back; if it can't, the value shows
`unknown` rather than a stale guess.

**No periodic polling** (to spare the lock battery). State refreshes on: your
interactions, the **Refresh** button, and a single read at startup once
Bluetooth has seen the lock. A change made in the SwitchBot app shows up after a
Refresh press.

## Protocol

All commands are the plaintext `pySwitchbot` feeds into the encrypted envelope
(AES-CTR, key from the cloud / stored by the core integration):

```
READ : 57 0f 4f 04 01                       -> <status> <CFG> 00 00 00 80
WRITE: 57 0f 4e 04 01 00 <mask> <val> ff     -> echoes resulting <CFG>
       result = (current & ~mask) | (val & mask)
```

`CFG` byte (high bits `0xC0` are constant status flags):

```
bit 3 (0x08) = Quick Key enabled
bit 2 (0x04) = trigger: 1 = Double press (2), 0 = Single press (1)
bits 1-0 (0x03) = function: 0x02 Lock&Unlock | 0x01 Unlock-only | 0x00 Lock-only
```

Example writes: enable `…000808ff`, disable `…000800ff`, double `…000404ff`,
single `…000400ff`, Lock&Unlock `…000302ff`, Unlock-only `…000301ff`,
Lock-only `…000300ff`.

## Install

1. Copy this folder to `<config>/custom_components/switchbot_quickkey/`.
2. Restart Home Assistant.
3. Settings → Devices & Services → **Add Integration** → "SwitchBot Lock Quick Key".
4. Pick the lock (keys are pulled automatically from the SwitchBot integration).

## Status

Interim. The goal is to upstream this into
[`pySwitchbot`](https://github.com/sblibs/pySwitchbot) + the core `switchbot`
integration once the inferred opcodes are field-validated.
