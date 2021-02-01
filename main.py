import adafruit_dotstar
from intellivision import Controller
import board
import gc
import pwmio
import usb_hid

gc.collect()

# Dot color mapped to first controller's direction, just for fun
dot = adafruit_dotstar.DotStar(board.APA102_SCK, board.APA102_MOSI, 1, brightness = 0.05)

# Led mapped to second controller's direction, just for fun
led = pwmio.PWMOut(board.D13)

# Controller 1
c1Pins = (board.A0, board.A1, board.A2, board.A3, board.A4, board.A5, board.SCK, board.MOSI, board.MISO)
controller1 = Controller(usb_hid.devices, 0, c1Pins)

# Controller 2
# Pin D5 cannot be used as input, we have to cut the solderable part of the header at this location and
# wire an input capable pin there, let say D4
c2Pins = (board.D1, board.SDA, board.SCL, board.D4, board.D7, board.D9, board.D10, board.D11, board.D12)
controller2 = Controller(usb_hid.devices, 1, c2Pins)

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

def colorDot(direction):
    dot[0] = wheel((direction - 1) * 16)

def fadeLed(direction):
    led.duty_cycle = 0 if direction == 0 else (2 ** 8) * 2 * direction

while True:
        controller1.update()
        colorDot(controller1.direction)

        controller2.update()
        fadeLed(controller2.direction)
