"""Constants + reverse-engineered Quick Key protocol for the SwitchBot Lock Ultra.

The "Quick Key" feature and
its sub-settings live in a SINGLE config byte on the lock, read/written over BLE:

    READ : 57 0f 4f 04 01                 -> reply: <status> <CFG> 00 00 00 80
    WRITE: 57 0f 4e 04 01 00 <mask> <val> ff   (masked write of the low nibble)
           reply echoes the resulting <CFG> byte (write is acknowledged)

CFG byte layout (low nibble; high bits 0xC0 are constant status flags):

    bit 3 (0x08) = Quick Key ENABLED        (1 = on)
    bit 2 (0x04) = trigger: 1 = DOUBLE press (2 presses), 0 = SINGLE press
    bits 1-0 (0x03) = function enum:
                      0b10 (0x02) = Lock & Unlock
                      0b01 (0x01) = Unlock Only
                      0b00 (0x00) = Lock Only

A masked write sets result = (current & ~mask) | (val & mask); the firmware
enforces mutual-exclusivity of the function enum bits.
"""

DOMAIN = "switchbot_quickkey"

# config-byte fields
BIT_ENABLE = 0x08
BIT_DOUBLE = 0x04
MASK_FUNCTION = 0x03

# read command (plaintext, pre-encryption)
CMD_READ = "570f4f0401"
# write template -> f"570f4e040100{mask:02x}{val:02x}ff"

# Function select (3-way). value = bits 1-0 of CFG.
FUNCTION_LABELS = {
    0x02: "Lock & Unlock",
    0x00: "Lock Only",
    0x01: "Unlock Only",
}
FUNCTION_OPTIONS = list(FUNCTION_LABELS.values())
FUNCTION_VALUES = {label: value for value, label in FUNCTION_LABELS.items()}

# Trigger select (2-way). value = bit 2 of CFG.
TRIGGER_SINGLE = "Single Press"
TRIGGER_DOUBLE = "Double Press"
TRIGGER_OPTIONS = [TRIGGER_SINGLE, TRIGGER_DOUBLE]

# NO periodic polling — it would needlessly connect over BLE and drain the lock
# battery. State refreshes only on: user interaction, the Refresh button, and a
# single read at startup (once Bluetooth has seen the lock).

# retry budgets (seconds) — ride out org.bluez.Error.InProgress contention with
# the core switchbot integration sharing the lock's single BLE radio.
# Every read (startup, Refresh button, post-write confirm) retries the full 15 s
# before giving up and reporting 'unknown'.
WRITE_DEADLINE_S = 15.0
READ_DEADLINE_S = 15.0
CONFIRM_READ_DEADLINE_S = 15.0
RETRY_BACKOFF_S = 0.5
