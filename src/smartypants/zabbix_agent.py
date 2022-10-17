import json
import socket
import struct

import smartypants.config
from smartypants.zabbix import ZabbixMetric, ZabbixResponse


class ZabbixAgent:
    """Implement basic agent capabilities of sending metrics to Zabbix server.
    Zabbix doc: https://www.zabbix.com/documentation/current/en/manual/appendix/items/trapper
    """

    def __init__(self, c: smartypants.config.ZabbixConfig):
        # https://www.zabbix.com/documentation/current/en/manual/appendix/protocols/header_datalen
        self.protocol_header = b"ZBXD\1"  # see above comment for explanation
        self.c = c

    def connect(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server = self.c.zbx_server
        port = self.c.zbx_port
        s.settimeout(self.c.zbx_timeout)
        s.connect((server, port))
        self.socket = s

    def disconnect(self):
        self.socket.close()

    def _build_message_data_dict(self, metric: ZabbixMetric):
        """Build a JSON dict ready to be sent to Zabbix API"""
        msg = {
            "request": "sender data",
            "data": [{"host": metric.host, "key": metric.key, "value": metric.value}],
        }
        msg_json = json.dumps(msg)
        return msg_json

    def _build_zabbix_message_header(self, data: str):
        # "<II" means: little endian, unsigned Int; https://docs.python.org/3.10/library/struct.html#struct.pack
        header = self.protocol_header + struct.pack("<II", len(data), 0)
        return header

    def _build_zabbix_message(self, data: str):
        header = self._build_zabbix_message_header(data)
        # message is just a concatenation of header and the byte encoded json string
        zabbix_message = header + data.encode()
        return zabbix_message

    def _get_zabbix_response_from_dict(self, response_dict: dict) -> ZabbixResponse:
        # TODO: handle this using pydantic's deserialization
        if response_dict["response"] == "success":
            response_dict = response_dict["info"]
            response_dict = response_dict.split(";")
            processed = response_dict[0].split(":")[1]
            failed = response_dict[1].split(":")[1]
            total = int(response_dict[2].split(":")[1])
            seconds_spent = response_dict[3].split(":")[1]
            data = ZabbixResponse(
                success=True,
                processed=processed,
                failed=failed,
                total=total,
                seconds_spent=seconds_spent,
            )
        else:
            data = ZabbixResponse(
                success=False, processed=0, failed=0, total=0, seconds_spent=0
            )
        return data

    def _decode_response(self, data_raw) -> dict:
        # raw data consists of header, data lenght and the actual data json
        # so we break it down accordingly
        # header is 5 bytes long
        # length field is 8 bytes
        data_lenght_raw = data_raw[5:13]
        # we don't really need the lenght, as we can slice it from 14th byte onwards, but we decode it anyways, so that we can use the lenght in unittests to make sure we are decoding correctly
        data_lenght = struct.unpack("<II", data_lenght_raw)[0]
        data_bytes = data_raw[13:]
        data = data_bytes.decode()
        data_lenght_actual = len(data)
        # data lenght from the message and our decoded one should match
        if data_lenght_actual != data_lenght:
            raise Exception("Data lenght not matching")
        data_json = json.loads(data)
        return data_json

    def get_response(self) -> ZabbixResponse:
        data_raw = self.socket.recv(200)
        data_json = self._decode_response(data_raw)
        return self._get_zabbix_response_from_dict(data_json)

    def send_message(self, metric: ZabbixMetric):
        msg_data_dict = self._build_message_data_dict(metric)
        zabbix_message = self._build_zabbix_message(msg_data_dict)
        self.socket.send(zabbix_message)

    def send_metric(self, metric: ZabbixMetric) -> ZabbixResponse:
        self.connect()
        self.send_message(metric)
        response = self.get_response()
        self.disconnect()
        return response

    def send_metric_and_check_success(self, metric: ZabbixMetric) -> bool:
        response = self.send_metric(metric)
        if response.success and response.processed == 1:
            return True
        return False
