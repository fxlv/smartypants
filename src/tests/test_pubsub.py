import string

import pytest
from smartypants import pubsub
from smartypants import config
from threading import Thread
from queue import Queue
from unittest.mock import Mock, call
from loguru import logger
from hypothesis import given, settings, HealthCheck
from hypothesis.strategies import text

import paho.mqtt.client as mqtt_client


@pytest.fixture
def pubsub_thread():
    c = config.Config()
    p = pubsub.PubSubThread(c)
    return p


@pytest.fixture
def test_msg():
    """A dummy mqtt message"""
    msg = Mock()
    msg.topic = "test topic"
    msg.payload = '{"test_key": "test_value"}'
    return msg


def test_PubSub_returns_a_thread():
    c = config.Config()
    p = pubsub.PubSubThread(c)
    assert isinstance(p, Thread)
    assert isinstance(p.q, Queue)


@given(topic=text())
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_combine_topic(pubsub_thread, topic):
    expected = f"{pubsub_thread.c.mqtt.base_topic}/{topic}"
    assert expected == pubsub_thread._combine_topic(topic)


@given(topic=text(alphabet=string.ascii_lowercase, min_size=2))
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_subscribe(pubsub_thread, caplog, topic):
    """
    Test that:
        * event was logged
        * topic was subscribed to
    """
    client = Mock()
    pubsub_thread._subscribe(client, topic)
    # validate that event was logged
    assert f"subscribing to {topic}" in caplog.text
    # should call client.subscribe(topic)
    client.subscribe.assert_called_with(topic)


def test_on_connect(pubsub_thread, caplog):
    client = Mock()
    userdata = Mock()
    flags = Mock()
    rc = 1
    pubsub_thread._subscribe = Mock()
    pubsub_thread.on_connect(client, userdata, flags, rc)
    # check that message was logged
    assert f"Connected with result code {rc}" in caplog.text
    # check that _subscribe() is called on all devices
    assert pubsub_thread._subscribe.call_count == len(
        pubsub_thread.c.zigbee_devices.devices
    )


def test_get_mqtt_message(pubsub_thread, test_msg):
    message_expected = {"payload": {"test_key": "test_value"}, "topic": "test topic"}
    message_actual = pubsub_thread._get_mqtt_message(test_msg)
    assert message_actual == message_expected


def test_on_message(pubsub_thread, test_msg, capsys):
    """
    Test that
        - received message is put into the queue
           by verifying that queue size increased
        - message is logged to stdout (for debugging)
    """
    qsize_before = pubsub_thread.q.qsize()
    client = Mock()
    userdata = Mock()
    pubsub_thread.on_message(client, userdata, test_msg)
    qsize_after = pubsub_thread.q.qsize()
    captured = capsys.readouterr()
    assert qsize_after == (qsize_before + 1)
    # verify that message was logged to stdout using devtools.debug()
    assert "test_value" in captured.out


def test_get_client(pubsub_thread):
    client = pubsub_thread._get_client()
    assert isinstance(client, mqtt_client.Client)


def test_run(pubsub_thread):
    pubsub_thread._get_client = Mock()  # mock out the mqtt client
    pubsub_thread.run()
    assert len(pubsub_thread._get_client.mock_calls) == 3
    calls = [
        call(),
        call().connect(
            pubsub_thread.c.mqtt.server,
            pubsub_thread.c.mqtt.port,
            pubsub_thread.c.mqtt.timeout,
        ),
        call().loop_forever(),
    ]
    pubsub_thread._get_client.assert_has_calls(calls)
