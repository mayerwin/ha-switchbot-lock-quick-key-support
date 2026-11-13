"""Constants + Quick Key protocol for the SwitchBot Lock Ultra.

The "Quick Key" feature and its sub-settings live in a SINGLE config byte on the
lock, read/written over BLE:

    READ : 57 0f 4f 04 01                      -> reply: <status> <CFG> <..> <motor> ..
    WRITE: 57 0f 4e 04 01 00 <update> <val> <motor>
           reply echoes the resulting <CFG> byte (write is acknowledged)

CFG byte layout (SwitchBot's protocol for this command, as quoted by a SwitchBot
developer on sblibs/pySwitchbot#515):

    bit 7 (0x80) = light                    (lock property, not Quick Key)
    bit 6 (0x40) = sound                    (lock property, not Quick Key)
    bit 4 (0x10) = manual-unlock linkage    (lock property, not Quick Key)
    bit 3 (0x08) = Quick Key ENABLED        (1 = on)
    bit 2 (0x04) = trigger: 1 = DOUBLE press (2 presses), 0 = SINGLE press
    bits 1-0 (0x03) = function enum:
                      0b10 (0x02) = Lock & Unlock
                      0b01 (0x01) = Unlock Only
                      0b00 (0x00) = Lock Only

<update> is a FIELD SELECTOR, not a per-bit mask: bits 7, 6, 4, 3 and 2 select
the matching single-bit field, and bit 1 alone selects the whole 2-bit function
field. Bit 0 is not a selector. Releases up to 0.3.2 sent 0x03 for the function;
that happened to work, but it set an undefined selector bit. Sending 0x02 was
checked on a Lock Ultra on 2026-11-12 for all six function transitions, with the
other bits untouched each time. <motor> 0xFF keeps the motor speed unchanged.

Bits 7-6 differ between locks because they are user settings (light and sound),
so nothing here validates them: an earlier release treated 0xC0 as a protocol
constant and silently discarded every reply from a lock with sound turned off
(issue #1 on mayerwin/ha-switchbot-lock-quick-key-support, 2026-09-21).
"""

DOMAIN = "switchbot_quickkey"

# config-byte fields
BIT_ENABLE = 0x08
BIT_DOUBLE = 0x04
MASK_FUNCTION = 0x03
# update-byte selector for the whole function field (see docstring)
SEL_FUNCTION = 0x02

# read command (plaintext, pre-encryption)
CMD_READ = "570f4f0401"
# write template -> f"570f4e040100{update:02x}{val:02x}ff"

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
