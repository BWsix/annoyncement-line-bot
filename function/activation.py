import logging
import json
import typing


logger = logging.getLogger()
logger.setLevel(logging.INFO)


def respond(status_code: int, data: dict):
    # TODO: when the function errors out, this header is not returned and web client shows cors error

    return {
        'statusCode': status_code,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Content-Type': 'application/json'
        },
        'body': json.dumps(data)
    }


def lambda_handle_activation(event, _):
    import linebot_utils
    import db_utils

    logger.info("> activation")
    logger.info(event)

    body = json.loads(event["body"])
    group_id = typing.cast(dict, body).get("group_id", None)
    group_name = typing.cast(dict, body).get("group_name", None)
    invite_code = typing.cast(dict, body).get("invite_code", None)

    if not type(group_id) is str:
        return respond(200, {"status": "error", "data": "Bad input"})
    if not type(group_name) is str:
        return respond(200, {"status": "error", "data": "Bad input"})
    if not type(invite_code) is str:
        return respond(200, {"status": "error", "data": "Bad input"})

    receivingGroup = db_utils.ReceivingGroup(
        group_id.strip(), group_name.strip())

    table = db_utils.get_table()
    controllingGroup = db_utils.ControllingGroup.from_table(table)

    if invite_code.strip() != controllingGroup.invite_code:
        logger.info(f"invalid invite_code: {invite_code}")
        return respond(200, {"status": "error", "data": "Invalid invite code"})
    if receivingGroup in controllingGroup.receiving_groups:
        logger.info(f"already activated: {group_id}")
        return respond(200, {"status": "error", "data": "Already activated"})

    controllingGroup.receiving_groups.append(receivingGroup)
    controllingGroup.save_to_table(table)

    message1 = "Annoyncement bot has been successfully configured!"
    linebot_utils.push_text([group_id], [message1], silence=True)

    message1 = f"{receivingGroup.group_name} is now receiving annoyncement"
    linebot_utils.push_text([controllingGroup.group_id], [
                            message1], silence=True)

    message = \
        "Annoyncement bot has been successfully configured!\n"\
        "Check the Line group for confirmation message."
    return respond(200, {"status": "success", "data": message})
