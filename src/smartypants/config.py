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


class Config:
    def __init__(self):
        config = configparser.ConfigParser()
        config.read("config.ini")
        config.sections()
        self.config: configparser.ConfigParser = config

    def get_zabbix_config(self) -> ZabbixConfig:
        return ZabbixConfig.parse_obj(self.config["zabbix"])
