import smartypants.zabbix
from smartypants import config
from threading import Thread
from smartypants import zabbix_agent
from smartypants import zabbix
from queue import Queue
import time
from devtools import debug
from smartypants.pubsub import MqttPublisher

from smartypants.datastructures import (
    TempSensor,
    Radiator,
    ZabbixKeyValue,
    LightBulbColor,
    LightBulbWarm,
    HueMotionSensor,
    Relay,
    Switch,
)


class UnknownDeviceException(Exception):
    """Raised when the device is not recognized"""


class Worker(Thread):
    """Worker consumes events from queue and does stuff with them"""

    def __init__(self, c: config.Config, q: Queue):
        self.c = c
        self.q = q
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
            debug(metric)
            debug(agent.send_metric_and_check_success(metric))

    def route_event(self, device):
        debug(device)
        if isinstance(device, Switch):
            mqtt = MqttPublisher(self.c)
            if device.payload.action == "on":
                print("Switching on")
                mqtt.on()
            elif device.payload.action == "off":
                print("Switching off")
                mqtt.off()

    def _consume_event(self, event):
        debug(event)
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
        elif "action" in event_dict["payload"] and "switch" in event_dict["topic"]:
            device = Switch(**event_dict)
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
