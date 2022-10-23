import json
from queue import Queue
from threading import Thread

import paho.mqtt.client as mqtt_client
from devtools import debug
from loguru import logger

from smartypants import config


def run_pubsub(c: config.Config):
    p_thread = PubSubThread(c)
    p_thread.start()


class PubSubThread(Thread):
    def __init__(self, c: config.Config):
        self.c: config.Config = c
        self.q = Queue()
        Thread.__init__(self)

    def _combine_topic(self, topic) -> str:
        """Combine the base_topic with device topic."""
        topic = f"{self.c.mqtt.base_topic}/{topic}"
        return topic

    def _subscribe(self, client, topic):
        """Wrapper around client.subscribe() which in addition to subscribing also logs the event."""
        logger.debug(f"subscribing to {topic}")
        client.subscribe(topic)

    def on_connect(self, client, userdata, flags, rc):
        logger.debug(f"Connected with result code {rc}")
        for topic in self.c.zigbee_devices.devices:
            self._subscribe(client, topic)

    def _get_mqtt_message(self, msg) -> dict:
        """
        Extract the topic and payload from MQTT message
        """
        message = {}
        message["topic"] = msg.topic
        message["payload"] = json.loads(msg.payload)
        return message

    def on_message(self, client, userdata, msg):
        self.q.put(self._get_mqtt_message(msg))
        debug(f"{msg.topic} / {msg.payload}")

    def _get_client(self):
        return mqtt_client.Client()

    def run(self):
        c = self.c  # just to make it shorter
        client = self._get_client()
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.connect(
            c.mqtt.server,
            c.mqtt.port,
            c.mqtt.timeout,
        )
        client.loop_forever()
