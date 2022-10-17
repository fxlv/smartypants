import configparser

from pydantic import BaseModel


class ZabbixConfig(BaseModel):
    api_server: str
    zbx_server: str
    zbx_port: int
    zbx_timeout: int
    host: str
    host_id: int
    token: str

class MqttConfig(BaseModel):
    server: str
    port: int
    timeout: int
    topic: str


class Config:
    def __init__(self):
        config = configparser.ConfigParser()
        config.read("config.ini")
        config.sections()
        self.config: configparser.ConfigParser = config
        self.zabbix = self._get_zabbix_config()
        self.mqtt = self._get_mqtt_config()

    def _get_zabbix_config(self) -> ZabbixConfig:
        return ZabbixConfig(**self.config["zabbix"])

    def _get_mqtt_config(self) -> MqttConfig:
        return MqttConfig(**self.config["mqtt"])
