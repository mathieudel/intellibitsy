import digitalio
import math
import struct
import time

def find_device(devices, index, usage_page, usage):
    """Search through the provided list of devices to find the ones with the matching usage_page and
    usage."""
    if hasattr(devices, "send_report"):
        devices = [devices]
    for i, device in enumerate(devices):
        if (
            device.usage_page == usage_page
            and device.usage == usage
            and hasattr(device, "send_report")
            and i == index
        ):
            return device
    raise ValueError("Could not find matching HID device.")

class Controller:
    
    # Keypad decoding
    _keypadMatrix = (0b10000001, 0b01000001, 0b00100001, 0b10000010, 0b01000010, 0b00100010, 0b10000100, 0b01000100, 0b00100100, 0b10001000, 0b01001000, 0b00101000)
    _buttonsMatrix = (0b01100000, 0b11000000, 0b10100000)

    # Discs decoding
    _discMask = 0b00011111
    _discMapping = {
        0b00000010:  1, 0b00000110:  2, 0b00010110:  3, 0b00010100:  4, 0b00000100:  5, 0b00001100:  6, 0b00011100:  7, 0b00011000:  8,
        0b00001000:  9, 0b00001001: 10, 0b00011001: 11, 0b00010001: 12, 0b00000001: 13, 0b00000011: 14, 0b00010011: 15, 0b00010010: 16
    }
    _discX = [0] #(0, *map(lambda a: int(round( 127 * math.cos(a * 0.125 * math.pi))), range(16)))
    _discY = [0] #(0, *map(lambda a: int(round(-127 * math.sin(a * 0.125 * math.pi))), range(16)))
    for i in range(16):
        _discX.append(int(round( 127 * math.cos(i * 0.125 * math.pi))))
        _discY.append(int(round(-127 * math.sin(i * 0.125 * math.pi))))

    def __init__(self, devices, index, pins):
        self._getCommonPin(pins[0])
        self._pins = list(map(self._getInputPin, pins[1:]))

        self._pins_state = 0
        self._buttons_state = 0
        self._direction = 0
        self._joy_x = 0
        self._joy_y = 0

        self._gamepad_device = find_device(devices, index, usage_page=0x1, usage=0x05)
        self._report = bytearray(5)
        self._last_report = bytearray(5)

        try:
            self._send(True)
        except OSError:
            time.sleep(1)
            self._send(True)

    def update(self):
        self._pins_state = 0
        for i, pin in enumerate(self._pins):
            self._pins_state |= pin.value << i

        self._buttons_state = 0
        # Read side buttons
        # Pressing two keypad buttons of different columns at the same time triggers a side button
        for i, mask in enumerate(self._buttonsMatrix):
            self._buttons_state |= ((self._pins_state & mask) == mask) << (i + 12)

        # Read keypad buttons if no side button has been pressed
        # but at least one of keypad column is set
        if (not self._buttons_state and self._pins_state & ~self._discMask):
            self._direction = 0 # We could keep previous direction instead of resetting it
            for i, mask in enumerate(self._keypadMatrix):
                self._buttons_state |= ((self._pins_state & mask) == mask) << i

        # Read disc if no keypad button has been pressed
        else:
            self._direction = self._discMapping.get(self._pins_state & self._discMask, 0)

        self._joy_x = self._discX[self._direction]
        self._joy_y = self._discY[self._direction]

        self._send(False)

    def _send(self, always):
        struct.pack_into(
            "<HBbb",
            self._report,
            0,
            self._buttons_state,
            self._pins_state,
            self._joy_x,
            self._joy_y,
        )

        if always or self._last_report != self._report:
            self._gamepad_device.send_report(self._report)
            self._last_report[:] = self._report

    @property
    def direction(self):
        return self._direction

    @staticmethod
    def _getCommonPin(pin):
        _pin = digitalio.DigitalInOut(pin)
        _pin.direction = digitalio.Direction.OUTPUT
        _pin.value = 1
        return _pin

    @staticmethod
    def _getInputPin(pin):
        _pin = digitalio.DigitalInOut(pin)
        _pin.direction = digitalio.Direction.INPUT
        _pin.pull = digitalio.Pull.DOWN
        return _pin
