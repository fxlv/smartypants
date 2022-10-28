from enum import IntEnum
from typing import Optional

from pydantic import BaseModel, Field
from pyzabbix import ZabbixAPI

import smartypants.config


class ZabbixItemType(IntEnum):
    """https://www.zabbix.com/documentation/current/en/manual/api/reference/item/object"""

    ZabbixTrapper = 2
    # Currently only supporting and testing with Type2, the zabbix trapper.


class ZabbixValueType(IntEnum):
    """https://www.zabbix.com/documentation/current/en/manual/api/reference/item/object
    Possible values:
    0 - numeric float;
    1 - character;
    2 - log;
    3 - numeric unsigned;
    4 - text.
    """

    numeric_float = 0
    character = 1
    log = 2
    numeric_unsigned = 3
    text = 4


class ZabbixMetric(BaseModel):
    host: str
    key: str
    value: object


class ZabbixItemDoesNotExist(Exception):
    """Raised when requested item does not exist"""

class ZabbixItem(BaseModel):
    itemid: Optional[int] = None
    hostid: str
    name: str
    # zabbix calls key "key_" so we support both options
    # this comes in handy when we deserialize from JSON response
    key: str = Field(alias="key_")
    type: ZabbixItemType
    value_type: ZabbixValueType

    class Config:
        # this is necessary for the Field Alias to work
        allow_population_by_field_name = True


class ZabbixResponse(BaseModel):
    success: bool
    processed: int
    failed: int
    total: int
    seconds_spent: float


class Zabbix:
    def __init__(self, c: smartypants.config.Config):
        self.c = c
        zapi = ZabbixAPI(c.config["zabbix"]["api_server"])
        zapi.login(api_token=c.config["zabbix"]["token"])
        self.zapi = zapi

    def get_host(self, host: str):
        host = self.zapi.host.get(filter={"host": host})
        assert len(host) == 1
        return host[0]

    # ability to create items
    def create_item(self, item: ZabbixItem) -> int:
        # based on example: https://github.com/lukecyca/pyzabbix/blob/master/examples/add_item.py
        # and zabbix api reference https://www.zabbix.com/documentation/current/en/manual/api
        item = self.zapi.item.create(
            hostid=item.hostid,
            name=item.name,
            key_=item.key,
            type=item.type,
            value_type=item.value_type.value,
        )
        assert isinstance(item, dict)  # it has to return a dict
        assert len(item["itemids"]) == 1
        return int(item["itemids"][0])

    def key_exists(self, key: str) -> bool:
        try:
            self.get_item_by_key(key)
        except ZabbixItemDoesNotExist:
            return False
        return True

    def get_item_by_key(self, key: str) -> ZabbixItem:
        # api doc for retrieving items https://www.zabbix.com/documentation/current/en/manual/api/reference/item/get
        retrieved_item = self.zapi.item.get(
            filter={"hostid": self.c.config["zabbix"]["host_id"], "key_": key}
        )
        if len(retrieved_item) != 1:
            raise ZabbixItemDoesNotExist
        zitem = ZabbixItem.parse_obj(retrieved_item[0])

        return zitem

    def delete_item(self, item_id: int) -> bool:
        delete_result = self.zapi.item.delete(item_id)
        if isinstance(delete_result, dict):
            if int(delete_result["itemids"][0]) == item_id:
                return True
        return False
