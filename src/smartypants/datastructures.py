from pydantic import BaseModel

from smartypants.zabbix import ZabbixValueType


class ZigbeeDevice:
    def zabbix_key(self) -> str:
        return self.topic.replace("/", "_")

    def get_zabbix_keys(self) -> list:
        return []  # by default no keys defined


class ZabbixKeyValue(BaseModel):
    topic: str
    key: str
    value: object
    value_type: ZabbixValueType

    def get_key(self) -> str:
        return f"{self.topic}_{self.key}".replace("/", "_")

    def get_name(self) -> str:
        return f"{self.topic} {self.key}".split("/")[
            1
        ]  # skip the topic name, only return the string after it


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
                value=self.payload.linkquality,
                value_type=ZabbixValueType.numeric_unsigned,
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
                value=int(self.payload.battery_low),
                value_type=ZabbixValueType.numeric_unsigned,
            )
        )
        kv_list.append(
            ZabbixKeyValue(
                topic=self.topic,
                key="link_quality",
                value=self.payload.linkquality,
                value_type=ZabbixValueType.numeric_unsigned,
            )
        )
        return kv_list


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
