# SwitchBot Lock Quick Key — Home Assistant integration (interim)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A small Home Assistant custom integration that exposes the **"Quick Key"** settings of
the **SwitchBot Lock Ultra** as native
HA entities, over Bluetooth LE.

The stock SwitchBot integration (and the underlying [`pySwitchbot`](https://github.com/sblibs/pySwitchbot)
library) don't expose these settings yet. This integration reverse-engineers the single
BLE config byte that holds them and surfaces it as entities, so you can read and change
the Quick Key from automations and dashboards.

> **Interim / temporary.** This is a stop-gap until native support lands upstream.
> Tracking PR: **[sblibs/pySwitchbot#515](https://github.com/sblibs/pySwitchbot/pull/515)**.
> When that merges, switch to the stock SwitchBot integration and remove this.

## What it exposes

On your existing Lock Ultra device, this adds:

| Entity | Type | Values |
|---|---|---|
| Quick Key function | `select` | `Lock & Unlock` · `Lock Only` · `Unlock Only` |
| Quick Key trigger | `select` | `Single Press` · `Double Press` |
| Quick Key | `switch` | enable / disable the Quick Key |
| Quick Key config byte | `sensor` (diagnostic) | raw `0xNN` |
| Quick Key refresh | `button` | re-read the byte over BLE on demand |

## Requirements

- The **core SwitchBot integration** already set up with your Lock Ultra (this provides
  `pySwitchbot` / `switchbot-ble` **and** the per-lock encryption keys — this integration
  *reuses the core integration's live BLE connection and keys*, it never opens its own
  second connection or stores secrets).
- Home Assistant **2024.1** or newer.
- Bluetooth working in HA (a Bluetooth adapter or an ESPHome Bluetooth proxy in range).

No extra Python requirements: `switchbot-ble` is already pulled in by the core integration.

## Installation

### HACS (recommended)

1. HACS → **⋮** → **Custom repositories**.
2. Repository: `https://github.com/mayerwin/ha-switchbot-lock-quick-key-support`, Category: **Integration**.
3. Install **SwitchBot Lock Quick Key (interim)**, then **restart Home Assistant**.
4. **Settings → Devices & Services → Add Integration → SwitchBot Lock Quick Key**, and pick your lock.

### Manual

Copy `custom_components/switchbot_quickkey/` into your HA `config/custom_components/`,
restart, then add the integration as above.

## How it works

The Quick Key feature and its sub-settings live in a **single config byte** on the lock,
read/written over BLE:

```
READ : 57 0f 4f 04 01            -> reply: <status> <CFG> 00 00 00 80
WRITE: 57 0f 4e 04 01 00 <mask> <val> ff   (masked write of the low nibble)
```

CFG byte (low nibble; high bits `0xC0` are constant status flags):

- bit 3 (`0x08`) = Quick Key **enabled**
- bit 2 (`0x04`) = trigger: 1 = **double** press, 0 = **single**
- bits 1-0 (`0x03`) = function: `0b10` Lock & Unlock · `0b01` Unlock Only · `0b00` Lock Only

To avoid the `org.bluez.Error.InProgress` contention that two connections to one lock
radio cause, this integration borrows the **live `SwitchbotLock` object** owned by the
core integration (`entry.runtime_data.device`) and serialises on its operation lock.
There is **no periodic polling** — it reads once at startup, on the Refresh button, and
after each write, to spare the lock's battery.

## Tested on

- **SwitchBot Lock Ultra**, firmware **V2.6**, via HA Bluetooth. All function/trigger/enable
  combinations write + read-back cleanly (verified end-to-end).

## License

MIT — see [LICENSE](LICENSE).
