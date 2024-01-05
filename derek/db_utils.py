from dataclasses import dataclass, asdict, field
import os
import typing

import boto3
from boto3_type_annotations.dynamodb import ServiceResource, Table

DYNAMODB_TABLE_NAME = os.getenv(
    'DYNAMODB_TABLE_NAME') or "annoyncement-line-bot"


def get_table():
    dynamodb = typing.cast(ServiceResource, boto3.resource('dynamodb'))
    return dynamodb.Table(DYNAMODB_TABLE_NAME)


@dataclass
class Group:
    group_id: str
    group_name: str


@dataclass
class ReceivingGroup(Group):
    pass


@dataclass
class ControllingGroup(Group):
    invite_code: str = field(default="")

    waiting_for_input: bool = field(default=False)
    user_invoked_command: str = field(default="")

    receiving_groups: list[ReceivingGroup] = field(default_factory=list)

    @staticmethod
    def from_table(table: Table):
        items = table.scan()["Items"]
        if len(items) != 1:
            raise Exception("Could not load from table: item_count != 1")

        data = typing.cast(dict, items[0])
        controllingGroup = ControllingGroup(
            group_id=data["group_id"],
            group_name=data["group_name"],
            invite_code=data["invite_code"],
            waiting_for_input=data["waiting_for_input"],
            user_invoked_command=data["user_invoked_command"],
        )

        for item in data.get("receiving_groups", []):
            controllingGroup.receiving_groups.append(ReceivingGroup(**item))

        return controllingGroup

    def save_to_table(self, table: Table):
        table.put_item(Item=asdict(self))
        print("Saved item table:", asdict(self))
