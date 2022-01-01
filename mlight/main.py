import json
import logging
from typing import Tuple

import paho.mqtt.client as mqtt
import typer

from mlight.bus import Bus

logging.basicConfig(level=logging.DEBUG)
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


def get_payload(payload: bytes) -> dict:
    return json.loads(payload.decode("utf-8"))

def message_factory(bus: Bus) -> callable:
    def on_message(client, userdata, msg) -> None:
        address, channel = decode_topic(msg.topic)
        
        payload = get_payload(msg.payload)

        brightness = payload["brightness"]
        if 0 > brightness > 64:
            raise MLightError("Brightness must be between 0 and 64")

        logger.debug(
            f"Setting brightness=%s at address=%s channel=%s ",
            brightness,
            address,
            channel,
        )
        bus.set(address, channel, brightness)

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


def main(
    server_address: str = "192.168.0.202",
    server_port: int = 1883,
    mqtt_username: str = "mlight",
    mqtt_password: str = "mlight",
    topic_prefix: str = "mlight",
    bus_address: str = "/tty/USB0",
    test: bool = False,
):
    bus = Bus(bus_address).start(test=test)

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
