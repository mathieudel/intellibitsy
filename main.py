import adafruit_dotstar
from adafruit_hid.gamepad import Gamepad
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
import board
import digitalio
import gc
import math
import time
import usb_hid

class Controller:

	def __init__(self, pins, keys, buttons):
		self._getCommonPin(pins[0])
		self._pins = list(map(self._getInputPin, pins[1:]))
		self._keys = keys
		self._buttons = buttons
		self._inputState = 0
		self._direction = -1

	def update(self):
		self._inputState = 0
		for i, pin in enumerate(self._pins):
			self._inputState |= pin.value << i

		# /!\ HACK /!\
		# Do not use keyboard.press, keyboard.release, gamepad.press_buttons or gamepad.release_buttons
		# since that would send an HID report each time.
		# That's 30 reports / loop for two controllers and seems to really slow down the driver.
		# Instead, directly mutate internal keyboard and gamepad states and send HID reports manually at the end of the main loop.

		for i, key in enumerate(self._keys):
			mask = keypadMatrix[i]
		 	if (self._inputState & mask) == mask: keyboard._add_keycode_to_report(key)
		 	else: keyboard._remove_keycode_from_report(key)

		for i, button in enumerate(self._buttons):
			mask = buttonsMatrix[i]
			if (self._inputState & mask) == mask: gamepad._buttons_state |= 1 << button - 1
			else: gamepad._buttons_state &= ~(1 << button - 1)

		if (self._inputState & ~discMask) == 0:
			self._direction = discMapping.get(self._inputState & discMask, 0)

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

gc.collect()

gamepad = Gamepad(usb_hid.devices)
keyboard = Keyboard(usb_hid.devices)

# Dot color mapped to first controller's direction, just for fun
dot = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1, brightness = 0.05)

# Keypad decoding
keypadMatrix = (0b10000001, 0b01000001, 0b00100001, 0b10000010, 0b01000010, 0b00100010, 0b10000100, 0b01000100, 0b00100100, 0b10001000, 0b01001000, 0b00101000)
buttonsMatrix = (0b01100000, 0b11000000, 0b10100000)

# Discs decoding
discMask = 0b00011111
discMapping = {
	0b00000010:  1, 0b00000110:  2, 0b00010110:  3, 0b00010100:  4, 0b00000100:  5, 0b00001100:  6, 0b00011100:  7, 0b00011000:  8,
	0b00001000:  9, 0b00001001: 10, 0b00011001: 11, 0b00010001: 12, 0b00000001: 13, 0b00000011: 14, 0b00010011: 15, 0b00010010: 16
}

discX = [0] #(0, map(lambda a: int(round( 127 * math.cos(a * 0.125 * math.pi))), range(16)))
discY = [0] #(0, map(lambda a: int(round(-127 * math.sin(a * 0.125 * math.pi))), range(16)))
for i in range(16):
	discX.append(int(round( 127 * math.cos(i * 0.125 * math.pi))))
	discY.append(int(round(-127 * math.sin(i * 0.125 * math.pi))))

# Controller 1
c1Pins = (board.A0, board.A1, board.A2, board.A3, board.A4, board.A5, board.SCK, board.MOSI, board.MISO)
c1Keys = (
	Keycode.THREE, Keycode.FOUR, Keycode.FIVE,
	Keycode.E,     Keycode.R,    Keycode.T,
	Keycode.D,     Keycode.F,    Keycode.G,
	Keycode.C,     Keycode.V,    Keycode.B
)
c1Buttons = (1, 2, 3)
controller1 = Controller(c1Pins, c1Keys, c1Buttons)

# Controller 2
c2Pins = (board.SDA, board.SCL, board.D5, board.D7, board.D9, board.D10, board.D11, board.D12, board.D13)
c2Keys = (
	Keycode.KEYPAD_SEVEN,  Keycode.KEYPAD_EIGHT, Keycode.KEYPAD_NINE,
	Keycode.KEYPAD_FOUR,   Keycode.KEYPAD_FIVE,  Keycode.KEYPAD_SIX,
	Keycode.KEYPAD_ONE,    Keycode.KEYPAD_TWO,   Keycode.KEYPAD_THREE,
	Keycode.KEYPAD_PERIOD, Keycode.KEYPAD_ZERO,  Keycode.KEYPAD_ENTER
)
c2Buttons = (4, 5, 6)
controller2 = Controller(c2Pins, c2Keys, c2Buttons)

def wheel(pos):
    if (pos < 0):
        return [0, 0, 0]
    if (pos > 255):
        return [0, 0, 0]
    if (pos < 85):
        return [int(pos * 3), int(255 - (pos*3)), 0]
    elif (pos < 170):
        pos -= 85
        return [int(255 - pos*3), 0, int(pos*3)]
    else:
        pos -= 170
        return [0, int(pos*3), int(255 - pos*3)]

while True:
	try:
		controller1.update()
		controller2.update()

		x = discX[controller1.direction]
		y = discY[controller1.direction]
		z = discX[controller2.direction]
		r_z = discY[controller2.direction]

		gamepad.move_joysticks(x, y, z, r_z)					# No need to manually send gamepad HID report after that
		keyboard._keyboard_device.send_report(keyboard.report)	# Manually send keyboard report now

		dot[0] = wheel((controller1.direction - 1) * 16)
		# time.sleep(0.01)

	except Exception as e:
		print("Exception: ", e)
