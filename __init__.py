# Header connections:
#
#       ^ this side is facing the SD card reader
#  3.3v o o GND
#   GND o o 5V
#       o o
#       o o IO16/27 TX -> MH-Z19 RX
#       o o IO17/28 RX -> MH-Z19 TX
#   SDA o o SCL

import display
import neopixel
from math import ceil, pi, sin, sqrt
from time import sleep
from .mhz19 import MHZ19
import utime


# Activate LEDs to also switch on 5V power supply to the MH-Z19.
neopixel.enable()
neopixel.send(bytes(4 * [0]))

def clear_rect(rect):
    x, y, w, h = rect
    display.drawRect(x, y, w, h, True, 0xffffff)

def draw_dashed_line(x0, y0, x1, y1, color=0x000000, space=12):
    vx, vy = x1-x0, y1-y0
    l2 = sqrt(vx**2 + vy**2)
    vec_x, vec_y = vx/l2 * space, vy/l2 * space

    lx0, ly0 = x0, y0
    while True:
        lx1, ly1 = min(lx0 + vec_x, x1), min(ly0 + vec_y, y1)
        display.drawLine(
            int(lx0), int(ly0),
            int(min(lx0 + vec_x/2, x1)), int(min(ly0 + vec_y/2, y1)),
            color)
        if lx1 == x1 and ly1 == y1:
            break
        lx0, ly0 = lx1, ly1
    display.drawPixel(x1, y1, color)


def draw_history_graph_plot(rect, history):
    x, y, w, h = rect

    if len(history) == 0:
        return

    sample_min, sample_max = min(history), max(history)
    sample_scale = 1.0 / max((sample_max-sample_min), 1)
    plot = [
        (x+i + (w-len(history)), y + int(h - (sample - sample_min) * sample_scale * h - 1))
        # history[-1] is the most recent sample.
        for i, sample in enumerate(history[max(-w, -len(history)):-1])
    ]
    for (x0, y0), (x1, y1) in zip(plot, plot[1:]):
        display.drawLine(x0, y0, x1, y1, 0x000000)


def draw_history_graph(rect, history, x_axis_labels):
    x, y, w, h = rect
    clear_rect(rect)

    txt_h = display.getTextHeight('-') + 2
    x_label_h = txt_h

    sample_min, sample_max = min(history), max(history)
    display.drawText(x, y, '%dppm' % sample_max, 0x000000)
    display.drawText(x, y-txt_h+h - x_label_h, '%dppm' % sample_min, 0x000000)
    draw_dashed_line(x, y, x+w-1, y, 0x000000)
    draw_dashed_line(x, y+h-1 - x_label_h, x+w-1, y+h-1 - x_label_h, 0x000000)

    for sample_offset, label in x_axis_labels.items():
        lx = x + w - sample_offset
        if lx > display.size()[0]:
            continue
        draw_dashed_line(lx, y, lx, y+h-1 - x_label_h, 0x000000)
        display.drawText(lx, y+h-txt_h, label)

    draw_history_graph_plot((x, y, w, h - x_label_h), history)


def draw_co2_label(rect, co2):
    x, y, w, h = rect
    clear_rect(rect)

    co2_label = 'CO2: %d' % co2
    co2_label_w = display.getTextWidth(co2_label, 'permanentmarker22')
    co2_label_h = display.getTextHeight(co2_label, 'permanentmarker22')
    display.drawText(x + w//2 - co2_label_w//2, y + h//2 - co2_label_h//2,
                     co2_label, 0x000000, 'permanentmarker22')


class UI:
    def __init__(self):
        self.co2_now = None
        self.co2_history_hash = None
        self.timestamps = None
        display.drawFill(0xffffff)  # Clear

    def draw(self, co2_now, co2_history, timestamps):
        w, h = display.size()
        co2_history_hash = hash(tuple(co2_history))
        if co2_now != self.co2_now:
            draw_co2_label((0, 0, w, h//4), co2_now)
        if co2_history_hash != self.co2_history_hash or self.timestamps != self.timestamps:
            draw_history_graph((0, h//4, w, h//4*3), co2_history, timestamps)
        if co2_now != self.co2_now or co2_history_hash != self.co2_history_hash or self.timestamps != self.timestamps:
            display.flush()

        # Cache rendered values so we can prevent repainting parts of the screen.
        self.co2_now = co2_now
        self.co2_history_hash = hash(tuple(co2_history))
        self.timestamps = timestamps


def history_timestamps(rate, max_sample_index):
    (_, _, _, now_h, now_m, now_s, _, _) = utime.localtime()
    now_s += now_m * 60

    offset = int(now_s / rate)
    labels = {}
    for i in range(ceil(max_sample_index / (1800/rate))):
        labels[offset + int(3600/rate) * i - int(1800/rate)] = '%d:30' % (now_h - i)
        labels[offset + int(3600/rate) * i] = '%d:00' % (now_h - i)
    return labels


history_rate = 30

mhz19 = None
co2_history = []
co2_history_add_counter = 0
co2_history_max_len = display.size()[0]
co2 = None
co2_show = None
co2_show_accum = []
co2_show_accum_max_len = 4
ui = UI()

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
    if co2_history_add_counter == 0:
        co2_history.append(co2)
        if len(co2_history) > co2_history_max_len:
            _ = co2_history.pop(0)
    co2_history_add_counter = (co2_history_add_counter+1) % history_rate

    co2_show_accum.append(co2)
    if len(co2_show_accum) >= co2_show_accum_max_len or co2_show is None:
        co2_show = sum(co2_show_accum) / len(co2_show_accum)
        co2_show_accum = []

    ui.draw(
        co2_now=co2_show,
        co2_history=co2_history,
        timestamps=history_timestamps(history_rate, co2_history_max_len),
    )
    sleep(1)
