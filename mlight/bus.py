import logging
import random
import time
from threading import Thread
from typing import Iterable, Optional, Union, List, Dict

import serial

from mlight.constants import DEFAULT_BRIGHTNESS

logger = logging.getLogger(__name__)

FLUSH_PERIOD = 0.001

Address = int
# Brightness is always between 0 and 64
Brightness = int
Brightnesses = List[Brightness]


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


def serial_factory(port):
    return serial.Serial(port, 9600)


class Bus:
    N_SLAVES = 5

    def __init__(self, port: str, send_interval_ms: int = 100):
        self.serial = serial_factory(port)
        # we index slaves from zero
        self.settings: Dict[Address, Brightnesses] = {}
        self.before_off_settings: Dict[Address, Brightnesses] = {}
        self.add_byte = {}
        self.last = {}
        self.send_interval_ms = send_interval_ms / 1000

    def set(self, address: Address, channel: int, value: Optional[Brightness]) -> None:
        if address not in self.settings:
            self.settings[address] = [0] * 4
            self.before_off_settings[address] = self.before_off_settings.get(address, {})

        if value is None:
            # if switching on without brightness, try to restore the previous one
            # fallback to DEFAULT_BRIGHTNESS
            # TODO: this feel like wrong layers
            logger.debug(
                "Restoring previous brightness for address %s, channel %s",
                address,
                channel,
            )
            value = self.before_off_settings[address].get(channel, DEFAULT_BRIGHTNESS)
        elif value == 0 and address in self.before_off_settings:
            # save original brightness before nulling
            logger.debug(
                "Saving brightness %s for address %s, channel %s",
                value, address, channel,
            )
            self.before_off_settings[address][channel] = self.settings[address][channel]

        self.settings[address][channel] = value

        logger.debug(
            "Set bus state on address=%s channel=%s to brightness=%s",
            address,
            channel,
            value,
        )
        return self.settings[address][channel]

    def set_all(self, addr, values: Union[Iterable, int]):
        if isinstance(values, int):
            values = [values] * 4
        self.settings[addr] = list(values)

    def _send_thread(self):
        for addr, chans in list(self.settings.items()):
            chans = tuple(chans)
            if addr in self.last and addr in self.add_byte and self.last[addr] == chans:
                add_b = self.add_byte[addr]
            else:
                add_b = self.add_byte[addr] = random.randrange(256)
            self.send_msg((addr,) + chans + (add_b,))
            self.last[addr] = tuple(chans)

            if not any(chans):
                logger.debug(
                    "Removing address %s from settings. All channels are 0.", addr
                )
                # TODO: feels hackish
                del self.settings[addr]

    def send_thread(self):
        while True:
            self._send_thread()
            self.serial.flush()
            time.sleep(self.send_interval_ms)

    def send_bytes(self, bs):
        for b in bs:
            self.serial.write(bytes([b]))
            self.serial.flush()
            time.sleep(FLUSH_PERIOD)

    def send_msg(self, msg):
        logger.debug("Sending: %s", msg)
        self.send_bytes(wrap_msg(msg))

    def send_debug_message(self):
        print("Running a test variant!")
        while True:
            self.send_bytes(bs=str(self.settings.items()).encode() + b"\n\n")
            self.serial.flush()
            time.sleep(5)

    def start(self, test=False):
        self.thread = Thread(
            target=self.send_thread if not test else self.send_debug_message
        )
        self.thread.daemon = True
        self.thread.start()
        return self
