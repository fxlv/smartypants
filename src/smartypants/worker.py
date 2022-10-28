import smartypants.zabbix
from smartypants import config
from threading import Thread
from smartypants import zabbix_agent
from smartypants import zabbix
from queue import Queue
import time
from devtools import debug
from pydantic import BaseModel


class ZigbeeDevice:

    def zabbix_key(self) -> str:
        return self.topic.replace("/", "_")

class TempSensorPayload(BaseModel):
    battery: float
    humidity: float
    linkquality: int
    pressure: float
    temperature: float
    voltage: float


class TempSensor(BaseModel, ZigbeeDevice):
    topic: str
    payload: TempSensorPayload


class RadiatorPayload(BaseModel):
    anti_scaling: str
    away_mode: str
    battery_low: bool
    child_lock: str
    current_heating_setpoint: float
    frost_detection: str
    linkquality: int
    local_temperature: float
    local_temperature_calibration: float
    preset_mode: str
    system_mode: str
    window_detection: str


class Radiator(BaseModel, ZigbeeDevice):
    topic: str
    payload: RadiatorPayload



class UnknownDeviceException(Exception):
    """Raised when the device is not recognized"""


class Worker(Thread):
    """Worker consumes events from queue and does stuff with them"""

    def __init__(self, c: config.Config, q: Queue):
        self.c = c
        self.q = q
        Thread.__init__(self)

    def send_to_zabbix(self, device):
        zbx = zabbix.Zabbix(self.c)
        agent = zabbix_agent.ZabbixAgent(self.c.zabbix)
        if not zbx.key_exists(device.zabbix_key()):
            item = smartypants.zabbix.ZabbixItem(
                itemid=None,
                hostid=self.c.zabbix.host_id,
                name=device.topic,
                key=device.zabbix_key(),
                type=smartypants.zabbix.ZabbixItemType.ZabbixTrapper,
                value_type=smartypants.zabbix.ZabbixValueType.numeric_float,
            )
            zbx.create_item(item)
        if isinstance(device, Radiator):
            metric = zabbix.ZabbixMetric(
                host=self.c.zabbix.host,
                key=device.zabbix_key(),
                value=device.payload.local_temperature,
            )
            agent.connect()
            debug(agent.send_metric_and_check_success(metric))

    def _consume_event(self, event):
        debug(event)
        ob = self._object_from_event(event)
        print(ob)
        self.send_to_zabbix(ob)

    def _object_from_event(self, event_dict):
        device = None
        if "radiator" in event_dict["topic"]:
            device = Radiator(**event_dict)
        elif "sensor" in event_dict["topic"]:
            device = TempSensor(**event_dict)
        else:
            raise UnknownDeviceException
        return device

    def run(self):
        print("thread running???")
        while True:
            print(self.q.qsize())
            self._consume_event(self.q.get())
            time.sleep(5)
