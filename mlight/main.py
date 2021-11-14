import logging
import typer

import paho.mqtt.client as mqtt

from mlight.bus import Bus

logging.basicConfig()
logger = logging.getLogger(__name__)


def message_factory(bus: Bus) -> function:
    def on_message(client, userdata, msg) -> None:
        # <prefix>/<address>/<channel>/set
        *_, address, channel, _ = msg.topic.split("/")
        brightness = msg.get("brightness")
        bus.set(address, channel, brightness)
    return on_message


def client_factory(on_message: function) -> mqtt.Client:
    client = mqtt.Client()
    client.on_message = on_message
    return client


def main(
    server_address: str = "192.168.0.202",
    server_port: int = 1883,
    topic_prefix: str = "mlight",
    bus_address: str = "/tty/USB0",
):
    bus = Bus(bus_address).start()

    callback = message_factory(bus)
    client = client_factory(callback)

    client.connect(server_address, server_port, 60)
    client.subscribe(f"{topic_prefix}/#" if not topic_prefix.endswith("/#") else topic_prefix)

    try:
        client.loop_forever()
    except KeyboardInterrupt:
        typer.echo("Interrupted by keyboard. Bye!")


if __name__ == "__main__":
    typer.run(main)
