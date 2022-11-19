import smartypants.zabbix
from smartypants import config
from threading import Thread
from smartypants import zabbix_agent
from smartypants import zabbix
from queue import Queue
import time
from devtools import debug
from smartypants.pubsub import MqttPublisher
import arrow

from smartypants.datastructures import (
    TempSensor,
    Radiator,
    ZabbixKeyValue,
    LightBulbColor,
    LightBulbWarm,
    HueMotionSensor,
    Relay,
    Switch,
    DoorSensor,
    Light,
)

from smartypants.statekeeper import StateKeeper


class UnknownDeviceException(Exception):
    """Raised when the device is not recognized"""


class Worker(Thread):
    """Worker consumes events from queue and does stuff with them"""

    def __init__(self, c: config.Config, q: Queue, s: StateKeeper):
        self.c = c
        self.q = q
        self.s = s
        Thread.__init__(self)

    def create_key_if_not_exists(self, key_value: ZabbixKeyValue):

        zbx = zabbix.Zabbix(self.c)
        key = key_value.get_key()
        name = key_value.get_name()
        if not zbx.key_exists(key):
            item = smartypants.zabbix.ZabbixItem(
                itemid=None,
                hostid=self.c.zabbix.host_id,
                name=name,
                key=key,
                type=smartypants.zabbix.ZabbixItemType.ZabbixTrapper,
                value_type=key_value.value_type,
            )
            zbx.create_item(item)

    def send_to_zabbix(self, device):
        # each device can implement get_zabbix_keys()
        # which returns a List[ZabbixKeyValue]
        # this method then iterates over them and calls send_to_zabbix_key() on each of them
        agent = zabbix_agent.ZabbixAgent(self.c.zabbix)

        zabbix_keys = device.get_zabbix_keys()
        if len(zabbix_keys) == 0:
            # no keys, nothing to send
            return False

        for key in zabbix_keys:
            self.create_key_if_not_exists(key)
            metric = zabbix.ZabbixMetric(
                host=self.c.zabbix.host,
                key=key.get_key(),
                value=key.value,
            )
            agent.connect()
            debug(agent.send_metric_and_check_success(metric))

    def route_event(self, device):
        self.s.add_device(device)
        mqtt = MqttPublisher(self.c, self.s)
        if isinstance(device, Switch):
            if "entrance" in device.topic:
                if device.payload.action == "on":
                    print("Switching on")
                    mqtt.hallway_on()
                elif device.payload.action == "off":
                    print("Switching off")
                    mqtt.hallway_off()
            elif "wc" in device.topic:
                if device.payload.action == "on":
                    print("Switching on")
                    mqtt.wc_on()
                elif device.payload.action == "off":
                    print("Switching off")
                    mqtt.wc_off()
        elif isinstance(device, DoorSensor):
            print("Door sensor triggered")
            if "entrance" in device.topic:
                door_sensor = self.s.get_device_by_topic(device.topic)
                hallway1 = self.s.get_device_by_topic("zigbee1/hallway_1")
                if not hallway1 or not door_sensor:
                    print("either hallway or sensor state missing")
                    return
                time_now = arrow.get()
                if (time_now - hallway1.timestamp).seconds > 20:
                    print("Timeout passed, acting")
                    # door sensor can trigger light only if the light state has not changed within last 30 sec
                    if door_sensor.is_open():
                        print("Door is open")
                        if arrow.get().time().hour > 16:
                            # only trigger in the evening
                            mqtt.hallway_on()
                        else:
                            print("Door open, but time not matching")
                else:
                    print("Light state already changed recently, ignoring")

    def _consume_event(self, event):
        ob = self._object_from_event(event)
        print("Consuming event")
        print(ob)
        self.send_to_zabbix(ob)
        self.route_event(ob)

    def _object_from_event(self, event_dict):
        device = None
        if "radiator" in event_dict["topic"]:
            device = Radiator(**event_dict)
        elif "sensor" in event_dict["topic"]:
            device = TempSensor(**event_dict)
        elif "light" in event_dict["topic"] and "color" in event_dict["payload"]:
            device = LightBulbColor(**event_dict)
        elif "light" in event_dict["topic"] and "color_temp" in event_dict["payload"]:
            device = LightBulbWarm(**event_dict)
        elif "motion" in event_dict["topic"]:
            device = HueMotionSensor(**event_dict)
        elif "switch" in event_dict["topic"]:
            device = Switch(**event_dict)
        elif "door" in event_dict["topic"]:
            device = DoorSensor(**event_dict)
        elif "hallway_" in event_dict["topic"]:
            device = Light(**event_dict)
        elif (
            "consumption" in event_dict["payload"]
            and "state_l1" in event_dict["payload"]
        ):
            device = Relay(**event_dict)
        else:
            raise UnknownDeviceException
        return device

    def run(self):
        print("thread running???")
        while True:
            print(f"Queue size: {self.q.qsize()}")
            self._consume_event(self.q.get())
            time.sleep(1)
