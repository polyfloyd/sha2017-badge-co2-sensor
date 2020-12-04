# Header connections:
#
#   ^ this side is facing the SD card reader
#   o o GND
#   o o 5V
#   o o
#   o o IO16/27 TX -> MH-Z19 RX
#   o o IO17/28 RX -> MH-Z19 TX
#   o o

import display
import neopixel
from math import pi, sin
from time import sleep
from .mhz19 import MHZ19


# Activate LEDs to also switch on 5V power supply to the MH-Z19.
neopixel.enable()
neopixel.send(bytes(4 * [0]))


def draw_history_graph(rect, history):
    x, y, w, h = rect

    if len(history) == 0:
        return

    sample_min, sample_max = min(history), max(history)
    sample_scale = 1.0 / max((sample_max-sample_min), 1)
    plot = [
        (x+i + (w-len(history)), y + int((sample - sample_min) * sample_scale * h))
        # history[-1] is the most recent sample.
        for i, sample in enumerate(history[max(-w, -len(history)):-1])
    ]
    for (x0, y0), (x1, y1) in zip(plot, plot[1:]):
        display.drawLine(x0, y0, x1, y1, 0x000000)


def draw_co2_label(rect, co2):
    x, y, w, h = rect

    co2_label = 'CO2: %d' % co2
    co2_label_w = display.getTextWidth(co2_label, 'permanentmarker22')
    co2_label_h = display.getTextHeight(co2_label, 'permanentmarker22')
    display.drawText(x + w//2 - co2_label_w//2, y + h//2 - co2_label_h//2,
                     co2_label, 0x000000, 'permanentmarker22')


def draw_ui(co2_history):
    w, h = display.size()
    display.drawFill(0xffffff)  # Clear
    draw_co2_label((0, 0, w, h//2), co2_history[-1])
    draw_history_graph((0, h//2, w, h//2), co2_history)
    display.flush()


mhz19 = None
co2_history = []
while True:
    if mhz19 is None:
        mhz19 = MHZ19(rx_pin=17, tx_pin=16)
    try:
        co2 = mhz19.gas_concentration()
    except Exception as err:
        print(err)
        mhz19.close()
        mhz19 = None
        continue

    print('co2: %d' % co2)
    co2_history.append(co2)
    if len(co2_history) > display.size()[0]:
        _ = co2_history.pop(0)

    draw_ui(co2_history)
    sleep(1)
