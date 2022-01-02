from mlight.bus import Bus
from mlight.constants import DEFAULT_BRIGHTNESS
import pytest


@pytest.fixture
def bus(mocker):
    mocker.patch("mlight.bus.serial_factory")
    bus = Bus("nothing")
    bus.start()
    return bus


def test_added_address(bus):
    bus.set(0, 1, 30)
    bus.set(0, 3, 40)
    bus.set(2, 2, 10)
    assert {0: [0, 30, 0, 40], 2: [0, 0, 10, 0]} == bus.settings

def test_value_retrieval(bus):
    bus.set(0, 1, 30)
    bus.set(0, 1, 0)
    bus.set(0, 1, None)
    assert {0: [0, 30, 0, 0]} == bus.settings

def test_value_retrieval_non_existent(bus):
    bus.set(0, 1, None)
    assert {0: [0, DEFAULT_BRIGHTNESS, 0, 0]} == bus.settings

def test_address_removed_from_settings(bus):
    bus.set(0, 1, 30)
    bus.set(0, 3, 40)
    bus.set(2, 2, 10)
    assert {0: [0, 30, 0, 40], 2: [0, 0, 10, 0]} == bus.settings

    bus.set(2, 2, 0)
    bus._send_thread()

    assert {0: [0, 30, 0, 40]} == bus.settings
