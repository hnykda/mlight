"""attempt of rewrite"""

import random
import time
from threading import Thread

import serial


def RL(a, k):
    return (((a) << (k)) | ((a) >> (8 - (k)))) & 0xFF


def compute_csum(msg):
    csum = 0
    for b in msg:
        csum = RL(csum, 3)
        csum ^= b
    return csum


def wrap_msg(msg):
    return bytes([253]) + bytes(msg) + bytes([compute_csum(msg)])


class Bus:
    def __init__(self, port):
        self.serial = serial.Serial(port, 9600)
        self.settings = {x: [0, 0, 0, 0] for x in range(10)}
        self.add_byte = {}
        self.last = {}

    def send_thread(self, *a):
        while True:
            for addr, chans in list(self.settings.items()):
                chans = tuple(chans)
                if (
                    addr in self.last
                    and addr in self.add_byte
                    and self.last[addr] == chans
                ):
                    add_b = self.add_byte[addr]
                else:
                    add_b = self.add_byte[addr] = random.randrange(256)
                self.send_msg((addr,) + chans + (add_b,))
                self.last[addr] = tuple(chans)
            self.serial.flush()
            # time.sleep(0.005)

    def set(self, addr, channels, brightness):
        msg = (addr, *channels, brightness)
        self.send_bytes(wrap_msg(msg))

    def send_bytes(self, bs):
        for b in bs:
            self.serial.write(bytes([b]))
            self.serial.flush()
            time.sleep(0.001)

    def send_msg(self, msg):
        # msg format is 7 bytes: [<start_byt>, <addr>, <ch1_brightness>, <ch2_brightness>, <ch3_brightness>, <ch4_brightness>, <padding byte>, <csum>]
        self.send_bytes(wrap_msg(msg))
