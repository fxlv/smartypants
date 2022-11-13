import smartypants.zabbix
from smartypants import config
from threading import Thread
from smartypants import zabbix_agent
from smartypants import zabbix
from queue import Queue
import time
from devtools import debug
from pydantic import BaseModel
from smartypants.zabbix import ZabbixValueType


class ZabbixKeyValue(BaseModel):
    topic: str
    key: str
    value: object
    value_type: ZabbixValueType

    def get_key(self) -> str:
        return f"{self.topic}_{self.key}".replace("/","_")
    def get_name(self) -> str:
        return f"{self.topic} {self.key}".split("/")[1] # skip the topic name, only return the string after it


class ZigbeeDevice:
    def zabbix_key(self) -> str:
        return self.topic.replace("/", "_")

    def get_zabbix_keys(self) -> list:
        return []  # by default no keys defined


class LightBulbUpdate(BaseModel):
    state: str


class Color(BaseModel):
    hue: int
    saturation: int
    x: float
    y: float


class LightBulbColorPayload(BaseModel):
    brightness: int
    color: Color
    color_mode: str
    color_temp: int
    linkquality: int
    state: str
    update: LightBulbUpdate

class LightBulbWarmPayload(BaseModel):
    brightness: int
    color_mode: str
    color_temp: int
    linkquality: int
    state: str
    update: LightBulbUpdate

class LightBulbColor(BaseModel, ZigbeeDevice):
    topic: str
    payload: LightBulbColorPayload

class LightBulbWarm(BaseModel, ZigbeeDevice):
    topic: str
    payload: LightBulbWarmPayload

class HueUpdate(BaseModel):
    state: str

class HueMotionPayload(BaseModel):
    battery: int
    illuminance: float
    illuminance_lux: float
    linkquality: int
    occupancy: int
    temperature: float
    update: HueUpdate

class RelayPayload(BaseModel):
    consumption: float
    linkquality: int
    energy: float
    power: float
    temperature: float
    voltage: float
    state_l1: str
    state_l2: str
class HueMotionSensor(BaseModel, ZigbeeDevice):
    topic: str
    payload: HueMotionPayload
    def get_zabbix_keys(self) -> list[ZabbixKeyValue]:
        """Defines the keys that we want to send to zabbix."""
        kv_list = []
        kv_list.append(
            ZabbixKeyValue(
                topic=self.topic,
                key="illuminance_lux",
                value=self.payload.illuminance_lux,
                value_type=ZabbixValueType.numeric_float,
            )
        )
        kv_list.append(
            ZabbixKeyValue(
                topic=self.topic,
                key="occupancy",
                value=self.payload.occupancy,
                value_type=ZabbixValueType.numeric_unsigned,
            )
        )
        kv_list.append(
            ZabbixKeyValue(
                topic=self.topic,
                key="illuminance",
                value=self.payload.illuminance,
                value_type=ZabbixValueType.numeric_float,
            )
        )
        kv_list.append(
            ZabbixKeyValue(
                topic=self.topic,
                key="linkquality",
                value=self.payload.linkquality,
                value_type=ZabbixValueType.numeric_float,
            )
        )
        return kv_list

class Relay(BaseModel, ZigbeeDevice):
    topic: str
    payload: RelayPayload
    def get_zabbix_keys(self) -> list[ZabbixKeyValue]:
        """Defines the keys that we want to send to zabbix."""
        kv_list = []
        kv_list.append(
            ZabbixKeyValue(
                topic=self.topic,
                key="temperature",
                value=self.payload.temperature,
                value_type=ZabbixValueType.numeric_float,
            )
        )
        kv_list.append(
            ZabbixKeyValue(
                topic=self.topic,
                key="consumption",
                value=self.payload.consumption,
                value_type=ZabbixValueType.numeric_float,
            )
        )
        kv_list.append(
            ZabbixKeyValue(
                topic=self.topic,
                key="power",
                value=self.payload.power,
                value_type=ZabbixValueType.numeric_float,
            )
        )
        return kv_list

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
    def get_zabbix_keys(self) -> list[ZabbixKeyValue]:
        """Defines the keys that we want to send to zabbix."""
        kv_list = []
        kv_list.append(
            ZabbixKeyValue(
                topic=self.topic,
                key="humidity",
                value=self.payload.humidity,
                value_type=ZabbixValueType.numeric_float,
            )
        )
        kv_list.append(
            ZabbixKeyValue(
                topic=self.topic,
                key="temperature",
                value=self.payload.temperature,
                value_type=ZabbixValueType.numeric_float,
            )
        )
        kv_list.append(
            ZabbixKeyValue(
                topic=self.topic,
                key="pressure",
                value=self.payload.pressure,
                value_type=ZabbixValueType.numeric_float,
            )
        )
        kv_list.append(
            ZabbixKeyValue(
                topic=self.topic,
                key="voltage",
                value=self.payload.voltage,
                value_type=ZabbixValueType.numeric_float,
            )
        )
        kv_list.append(
            ZabbixKeyValue(
                topic=self.topic,
                key="battery",
                value=self.payload.battery,
                value_type=ZabbixValueType.numeric_float,
            )
        )
        kv_list.append(
            ZabbixKeyValue(
                topic=self.topic,
                key="link_quality",
                value = self.payload.linkquality,
                value_type=ZabbixValueType.numeric_unsigned
            )
        )
        return kv_list


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

    def get_zabbix_keys(self) -> list[ZabbixKeyValue]:
        """Defines the keys that we want to send to zabbix."""
        kv_list = []
        kv_list.append(
            ZabbixKeyValue(
                topic=self.topic,
                key="local_temperature",
                value=self.payload.local_temperature,
                value_type=ZabbixValueType.numeric_float,
            )
        )
        kv_list.append(
            ZabbixKeyValue(
                topic=self.topic,
                key="heating_setpoint",
                value=self.payload.current_heating_setpoint,
                value_type=ZabbixValueType.numeric_float,
            )
        )
        kv_list.append(
            ZabbixKeyValue(
                topic=self.topic,
                key="battery_low",
                value = int(self.payload.battery_low),
                value_type=ZabbixValueType.numeric_unsigned
            )
        )
        kv_list.append(
            ZabbixKeyValue(
                topic=self.topic,
                key="link_quality",
                value = self.payload.linkquality,
                value_type=ZabbixValueType.numeric_unsigned
            )
        )
        return kv_list


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

    def _consume_event(self, event):
        debug(event)
        ob = self._object_from_event(event)
        print("Consuming event")
        print(ob)
        self.send_to_zabbix(ob)

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
        elif "consumption" in event_dict["payload"] and "state_l1" in event_dict["payload"]:
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
