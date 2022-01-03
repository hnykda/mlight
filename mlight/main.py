import json
import logging
from enum import Enum
from typing import Literal, Optional, Tuple

import paho.mqtt.client as mqtt
import typer

from mlight.bus import Bus
from mlight.constants import DEFAULT_BRIGHTNESS

logger = logging.getLogger(__name__)




class MLightError(RuntimeError):
    pass


def decode_topic(topic: str) -> Tuple[int]:
    """the topic is in the format <prefix>/<address>/<channel>/set"""
    *_, _address, _channel, set_suffix = topic.split("/")

    if set_suffix != "set":
        raise MLightError("Topic doesn't end with `/set`")

    channel = int(_channel)
    if 0 > channel > 3:
        raise MLightError("Channel must be between 0 and 3")

    address = int(_address)
    if 1 > address > 255:
        raise MLightError("Address must be between 1 and 255")

    return address, channel


def get_state(msg) -> Literal["ON", "OFF"]:
    try:
        state = msg["state"]  # state must always be present
    except KeyError:
        raise MLightError("Message must contain a `state` key")

    if state not in {"ON", "OFF"}:
        raise MLightError("State must be either `ON` or `OFF`")

    return state


def get_brightness(msg):
    brightness = msg.get("brightness")
    if brightness and 0 > brightness > 64:
        raise MLightError("Brightness must be between 0 and 64")
    return brightness


def parse_payload(payload: bytes) -> Tuple[str, Optional[int]]:
    msg = json.loads(payload.decode("utf-8"))

    brightness = get_brightness(msg)
    state = get_state(msg)

    return state, brightness


def message_factory(bus: Bus) -> callable:
    def on_message(client, userdata, msg) -> None:
        address, channel = decode_topic(msg.topic)

        state, brightness = parse_payload(msg.payload)

        if state == "ON":
            if not brightness:
                logger.debug(
                    "No brightness received. Setting to None"
                )
                brightness = None
            logger.debug(
                f"Setting brightness=%s at address=%s channel=%s ",
                brightness,
                address,
                channel,
            )
            bus.set(address, channel, brightness)
        elif state == "OFF":
            logger.debug(
                "Setting OFF (brightness=0) at address=%s channel=%s", address, channel
            )
            bus.set(address, channel, 0)
        else:
            raise MLightError("Unknown behavior based on the received message")

    return on_message


def client_factory(
    on_message: callable,
    server_address: str,
    server_port: int,
    topic_prefix: str,
    username: str,
    password: str,
) -> mqtt.Client:
    client = mqtt.Client()
    client.on_message = on_message
    client.username_pw_set(username, password)

    client.connect(server_address, server_port)
    client.subscribe(
        f"{topic_prefix}/#" if not topic_prefix.endswith("/#") else topic_prefix
    )

    return client


class LoggingLevelType(str, Enum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


def main(
    server_address: str = "192.168.0.202",
    server_port: int = 1883,
    mqtt_username: str = "mlight",
    mqtt_password: str = "mlight",
    topic_prefix: str = "mlight",
    bus_address: str = "/tty/USB0",
    test: bool = False,
    # how long to wait between indvidual flushes of data to serial
    # the higher the less CPU it takes
    send_interval_ms: int = 100,
    logging_level: LoggingLevelType = LoggingLevelType.INFO,
):

    logging.basicConfig(level=getattr(logging, logging_level))

    bus = Bus(bus_address, send_interval_ms).start(test=test)

    callback = message_factory(bus)
    client = client_factory(
        callback,
        server_address,
        server_port,
        topic_prefix,
        mqtt_username,
        mqtt_password,
    )

    try:
        typer.echo("Listening for control events...")
        client.loop_forever()
    except KeyboardInterrupt:
        typer.echo("Interrupted by keyboard. Bye!")


if __name__ == "__main__":
    typer.run(main)
