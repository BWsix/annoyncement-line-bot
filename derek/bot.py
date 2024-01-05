import os
import time
import typing
import hashlib
import urllib.parse

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    ApiClient,
    MessagingApi,
)
from linebot.v3.webhooks import (
    JoinEvent,
    LeaveEvent,
    MessageEvent,
    TextMessageContent,
)

import db_utils
import linebot_utils


DASHBOARD_URL = os.getenv(
    'DASHBOARD_URL') or "https://localhost:3000/dashboard"

handler = WebhookHandler(linebot_utils.LINEBOT_SECRET)


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    print("> message event")

    if event.source.type != "group":
        raise Exception("Event not came from group")

    group_id = event.source.group_id
    print("group id:", group_id)
    user_id = event.source.user_id
    print("user id", user_id)
    event_message = typing.cast(str, event.message.text).strip()
    print("message:", event_message)

    table = db_utils.get_table()
    controllingGroup = db_utils.ControllingGroup.from_table(table)

    if not group_id == controllingGroup.group_id:
        raise Exception("Event not came from controlling group")

    if controllingGroup.invite_code == "":
        controllingGroup.invite_code = event_message
        controllingGroup.save_to_table(table)

        message1 = \
            "Okga!"
        message2 = \
            "Now, invite me to other groups and use the invite code to gain access to the dashboard."
        return linebot_utils.reply(event.reply_token,
                                   [message1, message2])

    if controllingGroup.waiting_for_input and user_id == controllingGroup.user_invoked_command:
        controllingGroup.waiting_for_input = False
        controllingGroup.user_invoked_command = ""
        controllingGroup.save_to_table(table)

        if event_message.lower() == "cancel":
            message1 = \
                "Cancelled."
            return linebot_utils.reply(event.reply_token,
                                       [message1])

        receiving_group_ids = [
            g.group_id for g in controllingGroup.receiving_groups
        ]
        annoyncement = \
            f"{event_message}"
        linebot_utils.push_text(receiving_group_ids, annoyncement)

        message1 = \
            "ok"
        return linebot_utils.reply(event.reply_token,
                                   [message1])

    if event_message.lower() == "annoy":
        controllingGroup.waiting_for_input = True
        controllingGroup.user_invoked_command = user_id
        controllingGroup.save_to_table(table)

        message1 = \
            "Hi there o/"
        message2 = \
            "Please enter annoyncement or type 'cancel' or 'Cancel' to cancel:"
        return linebot_utils.reply(event.reply_token,
                                   [message1, message2])


@handler.add(JoinEvent)
def handle_join(event):
    print("> join event")

    if event.source.type != "group":
        raise Exception("Event not came from group")

    group_id = event.source.group_id
    print("group id:", group_id)

    with ApiClient(linebot_utils.configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        group_summary = line_bot_api.get_group_summary(group_id)
    group_name = group_summary.group_name
    print("group name:", group_name)

    table = db_utils.get_table()
    item_count = table.scan()["Count"]
    joined_controlling_group = item_count == 0

    if joined_controlling_group:
        print("> bot joined controlling group")

        db_utils.ControllingGroup(
            group_id, group_name).save_to_table(table)

        current_time = str(time.time())
        hashed_time = hashlib.sha256(current_time.encode()).hexdigest()
        generated_invitation_code = hashed_time[:8]

        message1 = \
            "Hi, Derek here o/"
        message2 = \
            "Usage:\n"\
            "To make an annoyncement, type 'annoy' or 'Annoy' as a command in the group chat.\n"\
            "Wait for Derek's reply and send a message as an annoyncement."
        message3 = \
            "Before making annoyncements, let's first configure the invite code for the dashboard.\n"\
            "Below is a randomly generated string that you can use as an invite code:"
        message4 = \
            generated_invitation_code
        message5 = \
            "Now, please enter something into the chat as an invite code:"
        return linebot_utils.reply(event.reply_token,
                                   [message1, message2, message3, message4, message5])
    else:
        print("> bot joined receiving group")

        url_encoded_group_name = urllib.parse.quote(group_name)
        dashboard_url = f'{DASHBOARD_URL}?group_id={group_id}&group_name={url_encoded_group_name}'

        message1 = \
            "Hi, Derek here o/"
        message2 = \
            "Annoyncement line bot is a self-hosted annoyncement system developed by VFLC.\n"\
            "For more information please visit https://github.com/BWsix/annoyncement-line-bot"
        message3 = \
            "For group admins to configure the annoyncement bot, please visit the link below:\n"\
            f"{dashboard_url}"
        return linebot_utils.reply(event.reply_token,
                                   [message1, message2, message3])


@handler.add(LeaveEvent)
def handle_leave(event):
    print("> leave event")

    if event.source.type != "group":
        raise Exception("Event not came from group")

    group_id = event.source.group_id
    print("group id:", group_id)

    with ApiClient(linebot_utils.configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        group_summary = line_bot_api.get_group_summary(group_id)
    group_name = group_summary.group_name
    print("group name:", group_name)

    table = db_utils.get_table()
    controllingGroup = db_utils.ControllingGroup.from_table(table)

    receiving_group = db_utils.ReceivingGroup(group_id, group_name)
    if receiving_group in controllingGroup.receiving_groups:
        raise Exception("Event not came from receiving group")

    controllingGroup.receiving_groups.remove(receiving_group)
    controllingGroup.save_to_table(table)

    message = \
        f"{receiving_group.group_name} kicked me out of their group."
    return linebot_utils.push_text([controllingGroup.group_id], message)


def handle_lambda(event, context):
    body = event['body']
    signature = event['headers']['x-line-signature']

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return "Invalid signature. Please check your channel access token/channel secret."

    return 'ok'
