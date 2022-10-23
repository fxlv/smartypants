import configparser

from smartypants.config import Config


def test_config_instance_creation():
    c = Config()
    assert isinstance(c.config, configparser.ConfigParser)


def test_config_contains_expected_sections():
    c = Config()
    assert c.config.sections() == ["mqtt", "zigbee_devices", "zabbix"]


def test_config_contains_zabbix_paramaters():
    c = Config()
    zabbix_params = c.config["zabbix"]
    isinstance(zabbix_params["zbx_server"], str)


def test_config_contains_zigbee_devices():
    c = Config()
    zigbee_devices = c.config["zigbee_devices"]
    z1 = zigbee_devices["devices"]
    pass
