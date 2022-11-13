import json
from queue import Queue
from threading import Thread, Event

import paho.mqtt.client as mqtt_client
from devtools import debug
from loguru import logger

from smartypants import config
import time


def run_pubsub(c: config.Config):
    p_thread = PubSubThread(c)
    p_thread.start()
    return p_thread


class MqttPublisher:
    def __init__(self, config=config.Config):
        self.client = mqtt_client.Client()
        debug(config)
        self.client.connect(
            config.mqtt.server,
            config.mqtt.port,
            config.mqtt.timeout,
        )

    def wc_off(self):
        self.client.publish("zigbee1/wc_fan/set", '{"state_l1":"off"}')
        self.client.publish("zigbee1/guest_bathroom_floor/set", '{"state_l1":"off"}')
    def wc_on(self):
        self.client.publish("zigbee1/wc_fan/set", '{"state_l1":"on"}')
        self.client.publish("zigbee1/guest_bathroom_floor/set", '{"state_l1":"on"}')
    def hallway_on(self):
        self.client.publish("zigbee1/hallway_1/set", '{"state":"on"}')
        self.client.publish("zigbee1/hallway_2/set", '{"state":"on"}')
        self.client.publish("zigbee1/hallway_3/set", '{"state":"on"}')

    def hallway_off(self):
        self.client.publish("zigbee1/hallway_1/set", '{"state":"off"}')
        self.client.publish("zigbee1/hallway_2/set", '{"state":"off"}')
        self.client.publish("zigbee1/hallway_3/set", '{"state":"off"}')
        self.client.publish("zigbee1/hallway_4/set", '{"state":"off"}')
        self.client.publish("zigbee1/hallway_5/set", '{"state":"off"}')


class PubSubThread(Thread):
    def __init__(self, c: config.Config):
        self.c: config.Config = c
        self.q = Queue()
        self.stop_event = Event()
        Thread.__init__(self)
        self.daemon = True

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
            self._subscribe(client, self._combine_topic(topic))

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
        print(f"Pubsub> {msg.topic} / {msg.payload} / queue size: {self.q.qsize()}")

    def _get_client(self):
        return mqtt_client.Client()

    def _connect(self):
        c = self.c  # just to make it shorter
        client = self._get_client()
        client.on_connect = self.on_connect
        client.on_message = self.on_message
        client.connect(
            c.mqtt.server,
            c.mqtt.port,
            c.mqtt.timeout,
        )
        return client

    def run(self):
        client = self._connect()
        client.loop_start()
        while not self.stop_event.is_set():
            time.sleep(1)
        logger.debug("Stop event received")
        time.sleep(1)
        client.loop_stop()
