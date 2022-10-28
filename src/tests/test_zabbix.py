import json

import pytest
from pyzabbix import ZabbixAPI
import random

import smartypants.zabbix
from smartypants.config import Config, ZabbixConfig
from smartypants.zabbix import (
    Zabbix,
    ZabbixResponse,
    ZabbixMetric,
    ZabbixValueType,
    ZabbixItemType,
    ZabbixItem,
)
from smartypants.zabbix_agent import ZabbixAgent
import socket
from pydantic.error_wrappers import ValidationError


@pytest.fixture
def zbx():
    c = Config()
    zbx = Zabbix(c)
    return zbx


@pytest.fixture
def zbx_cfg():
    c = Config()
    return c.zabbix


@pytest.fixture
def zbx_agent(zbx_cfg):
    return ZabbixAgent(zbx_cfg)


@pytest.fixture
def test_metric():
    return ZabbixMetric(host="test_host", key="test_key", value="test_value")


class TestDataStructures:
    def test_ZabbixItemType(self):
        # only one type supported currently
        assert ZabbixItemType.ZabbixTrapper.value == 2

    def test_ZabbixValueType(self):
        assert ZabbixValueType.numeric_float.value == 0
        assert ZabbixValueType.character.value == 1
        assert ZabbixValueType.log.value == 2
        assert ZabbixValueType.numeric_unsigned.value == 3
        assert ZabbixValueType.text.value == 4

    def test_ZabbixMetric(self):
        """testing that the class behaves as expected"""
        zm = ZabbixMetric(host="testhost", key="test_key", value="test value")
        assert isinstance(zm, ZabbixMetric)
        zm1 = ZabbixMetric(host=111, key="test_key", value="test value")
        assert isinstance(zm1.host, str)  # pydantic takes care of casting to string
        assert isinstance(zm1, ZabbixMetric)
        with pytest.raises(TypeError):
            # all paramaters must be provided as key=value
            zm2 = ZabbixMetric("testhost", "test_key", "test value")

    def test_ZabbixItem_cannot_instantiate_without_arguments(self):
        with pytest.raises(ValidationError):
            # cannot instantiate without providing arguments
            zi = ZabbixItem()

    def test_ZabbixItem_only_valid_types_allowed(self):
        with pytest.raises(ValidationError):
            # there is no type 3, so this will throw validation error
            zi = ZabbixItem(
                hostid="test_hostid",
                name="test_name",
                key="test_key",
                type=3,
                value_type=1,
            )
        with pytest.raises(ValidationError):
            # there is no value_type 5, so this will throw validation error
            zi = ZabbixItem(
                hostid="test_hostid",
                name="test_name",
                key="test_key",
                type=2,
                value_type=5,
            )

    def test_ZabbixItem(self):
        zi = ZabbixItem(
            hostid="test_hostid", name="test_name", key="test_key", type=2, value_type=1
        )
        assert isinstance(zi, ZabbixItem)

    def test_ZabbixResponse(self):
        response = ZabbixResponse(
            success=True, processed=1, failed=1, total=1, seconds_spent=2
        )
        assert isinstance(response, ZabbixResponse)


class TestZabbixAgent:
    def test_connect_refused(self, zbx_cfg: ZabbixConfig):
        """Try to connect to localhost and verify how connection refused will be handled"""
        zbx_cfg.zbx_server = "127.0.0.1"
        agent = ZabbixAgent(zbx_cfg)
        with pytest.raises(ConnectionRefusedError):
            agent.connect()

    def test_connect_timeout(self, zbx_cfg: ZabbixConfig):
        """Try connecting to non-existing IP, to verify how timeout works"""
        zbx_cfg.zbx_server = "127.222.222.1"  # any non-existing IP would work
        zbx_cfg.zbx_timeout = (
            1  # decrease from default so we don't have to wait for too long
        )
        agent = ZabbixAgent(zbx_cfg)
        with pytest.raises(TimeoutError):
            agent.connect()

    def test_connect(self, zbx_cfg: ZabbixConfig):
        agent = ZabbixAgent(zbx_cfg)
        agent.connect()
        assert isinstance(agent.socket, socket.socket)

    def test_disconnect(self, zbx_cfg):
        """Test that disconnect actually disconnects.

        - Create agent, establish connection.
        - Send some data, jut to prove that socket works.
        - Then call disconnect()
        - Now, sending data will raise exception as the socket is no longer open
        """
        agent = ZabbixAgent(zbx_cfg)
        agent.connect()

        agent.socket.send(
            b"test"
        )  # does not matter what we send, just proves that socket is open
        agent.disconnect()
        with pytest.raises(OSError):
            agent.socket.send(
                b"test"
            )  # sending will raise exception now, as socket is no longer open

    def test_build_message_data_dict(self, zbx_agent: ZabbixAgent):
        """
        validate that the data dictionary that is returned, contains all the expected data
        as it is a string, then we first deserialize it and test the actual dictionary
        """
        metric = ZabbixMetric(host="test_host", key="test_key", value="test_value")
        data_dict = zbx_agent._build_message_data_dict(metric)
        data_dict_json = json.loads(data_dict)
        assert "request" in data_dict_json
        assert "data" in data_dict_json
        assert "host" in data_dict_json["data"][0]
        assert "key" in data_dict_json["data"][0]
        assert "value" in data_dict_json["data"][0]

    def test_build_message_header(self, zbx_agent: ZabbixAgent):
        test_data = "test data here"
        message_header = zbx_agent._build_zabbix_message_header(test_data)
        assert message_header == b"ZBXD\x01\x0e\x00\x00\x00\x00\x00\x00\x00"

    def test_build_zabbix_message(self, zbx_agent: ZabbixAgent):
        test_data = "test data here"
        message = zbx_agent._build_zabbix_message(test_data)
        assert message == b"ZBXD\x01\x0e\x00\x00\x00\x00\x00\x00\x00test data here"

    def test_get_zabbix_response_from_dict(self, zbx_agent: ZabbixAgent):
        response_dict = {
            "response": "success",
            "info": "processed: 0; failed: 1; total: 1; seconds spent: 0.000028",
        }
        response = zbx_agent._get_zabbix_response_from_dict(response_dict)
        assert isinstance(response, ZabbixResponse)
        assert response.failed == 1
        assert response.processed == 0

    def test_decode_response(self, zbx_agent: ZabbixAgent):
        data_raw = b'ZBXD\x01Z\x00\x00\x00\x00\x00\x00\x00{"response":"success","info":"processed: 0; failed: 1; total: 1; seconds spent: 0.000029"}'
        data_json_expected = {
            "response": "success",
            "info": "processed: 0; failed: 1; total: 1; seconds spent: 0.000029",
        }
        data_json_actual = zbx_agent._decode_response(data_raw)
        assert data_json_expected == data_json_actual

    def test_send_message(self, zbx_agent: ZabbixAgent, test_metric: ZabbixMetric):
        zbx_agent.connect()
        zbx_agent.send_message(test_metric)
        response = zbx_agent.get_response()
        assert response.success

    def test_get_response(self, zbx_agent: ZabbixAgent, test_metric):
        zbx_agent.connect()
        zbx_agent.send_message(test_metric)
        response = zbx_agent.get_response()
        assert isinstance(response, ZabbixResponse)

    def test_send_metric_and_check_success(self, zbx_agent: ZabbixAgent, test_metric):
        metric = ZabbixMetric(host=zbx_agent.c.host, key="test_key", value=8)
        zbx_agent.connect()
        assert zbx_agent.send_metric_and_check_success(metric)


def test_zabbix_instantiation_without_config_fails():
    with pytest.raises(TypeError):
        z = Zabbix()


def test_zabbix_instance_contains_zapi(zbx):
    assert isinstance(zbx.zapi, ZabbixAPI)


def test_zabbix_host_from_config_matches_host_id(zbx):
    """Verify that we are able to talk to Zabbix and test host exists"""
    host = zbx.get_host(zbx.c.config["zabbix"]["host"])
    assert host["hostid"] == zbx.c.config["zabbix"]["host_id"]


def test_add_remove_item(zbx):
    """Test adding and removing a zabbix item.
    While not part of Smartypants, we need to make sure this functionality works using the library.
    """
    randint = random.randint(1, 999)  # because that should be quite random enough
    test_key = f"test_key_created_by_smartypants_test_suite_{randint}"
    item = ZabbixItem(
        hostid=zbx.c.config["zabbix"]["host_id"],
        name="Test item (smartypants test suite)",
        key=test_key,
        type=ZabbixItemType.ZabbixTrapper,
        value_type=ZabbixValueType.numeric_float,
    )
    created_item_id = zbx.create_item(item)
    retrieved_item = zbx.get_item_by_key(test_key)
    assert created_item_id == retrieved_item.itemid
    assert retrieved_item.key == test_key
    # now, delete the item
    assert zbx.delete_item(retrieved_item.itemid)


def test_key_does_not_exist(zbx):
    with pytest.raises(smartypants.zabbix.ZabbixItemDoesNotExist):
        zbx.get_item_by_key("nonexistant")


def test_key_does_not_exist2(zbx):
    assert zbx.key_exists("nonexistant") == False


def test_send_metric_to_non_existing_key_fails(zbx_agent):
    # first send a metric to non-existant key, this will fail
    metric = ZabbixMetric(
        host=zbx_agent.c.host,
        key="test_key_nonexistant",
        value="test val 1",
    )
    response = zbx_agent.send_metric(metric)
    assert response.success
    assert response.processed == 0
    assert response.failed == 1


def test_send_metric(zbx_agent):
    randint = random.randint(1, 999)  # because that should be quite random enough
    metric = ZabbixMetric(host=zbx_agent.c.host, key="test_key", value=randint)
    response = zbx_agent.send_metric(metric)
    assert response.success
    assert response.processed == 1
    assert response.failed == 0
    assert response.success == 1
