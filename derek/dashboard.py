import os
import json
import typing

import db_utils
import linebot_utils

LINEBOT_ACCESS_TOKEN = os.getenv('LINEBOT_ACCESS_TOKEN')


DASHBOARD_URL = os.getenv(
    'DASHBOARD_URL') or "https://localhost:3000/dashboard"


def respond(status_code: int, data: dict):
    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin' : '*',
            'Access-Control-Allow-Headers':'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Content-Type': 'application/json'
        },
        'body': json.dumps(data)
    }


def handle_lambda(event, context):
    print("> activation")

    body = json.loads(event["body"])
    print(body)

    group_id = typing.cast(dict, body).get("group_id", None)
    print("group_id:", group_id)
    group_name = typing.cast(dict, body).get("group_name", None)
    print("group_name:", group_name)
    invite_code = typing.cast(dict, body).get("invite_code", None)
    print("invite_code", invite_code)

    if not type(group_id) is str:
        return respond(400, {"status": "error", "data": "Bad input"})
    if not type(group_name) is str:
        return respond(400, {"status": "error", "data": "Bad input"})
    if not type(invite_code) is str:
        return respond(400, {"status": "error", "data": "Bad input"})

    receivingGroup = db_utils.ReceivingGroup(
        group_id.strip(), group_name.strip())

    table = db_utils.get_table()
    controllingGroup = db_utils.ControllingGroup.from_table(table)

    if receivingGroup in controllingGroup.receiving_groups:
        return respond(400, {"status": "error", "data": "Bad input"})
    if invite_code.strip() != controllingGroup.invite_code:
        return respond(403, {"status": "error", "data": "Invalid invite code"})

    controllingGroup.receiving_groups.append(receivingGroup)
    controllingGroup.save_to_table(table)

    message = \
        "Annoyncement bot has been successfully configured!"
    linebot_utils.push_text([group_id], message, silence=True)

    message = \
        f"{receivingGroup.group_name} is now receiving annoyncement"
    linebot_utils.push_text([controllingGroup.group_id], message, silence=True)

    message = \
        "Annoyncement bot has been successfully configured!\n"\
        "Check the Line group for confirmation message."
    return respond(200, {"status": "success", "data": message})
