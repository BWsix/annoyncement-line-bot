import logging
import os
import time
import hashlib
import urllib.parse

from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import ApiClient, MessagingApi
from linebot.v3.webhooks import (
    AudioMessageContent,
    FileMessageContent,
    GroupSource,
    JoinEvent,
    MessageEvent,
    ImageMessageContent,
    TextMessageContent,
    VideoMessageContent,
)

import linebot_utils

logger = logging.getLogger()
logger.setLevel(logging.INFO)

handler = WebhookHandler(linebot_utils.LINEBOT_SECRET)


@handler.add(MessageEvent)
def handle_message(event: MessageEvent):
    import db_utils
    import s3_utils

    logger.info("> message event")
    if event.source is None:
        return logger.warn("> event with no source")
    if not isinstance(event.source, GroupSource):
        return logger.info("> event not came from group")

    message = event.message
    isTextMessage = isinstance(message, TextMessageContent)
    isImageMessage = isinstance(message, ImageMessageContent)
    isVideoMessage = isinstance(message, VideoMessageContent)
    isAudioMessage = isinstance(message, AudioMessageContent)
    isFileMessage = isinstance(message, FileMessageContent)

    group_id = event.source.group_id
    user_id = event.source.user_id
    if group_id is None or user_id is None:
        return logger.error("> no user or group id")
    logger.info(f"group id: {group_id}, user id: {user_id}")

    table = db_utils.get_table()
    controllingGroup = db_utils.ControllingGroup.from_table(table)

    if not group_id == controllingGroup.group_id:
        return logger.warn("Event not came from controlling group")

    if isTextMessage and controllingGroup.invite_code == "":
        controllingGroup.invite_code = message.text.strip()
        controllingGroup.save_to_table(table)

        message1 = "Okga!"
        message2 = "Now, invite me to other groups and use the invite code to gain access to the dashboard."
        return linebot_utils.reply(event.reply_token,
                                   [message1, message2])

    if isTextMessage and message.text.strip().lower() == "annoy":
        controllingGroup.waiting_for_input = True
        controllingGroup.user_invoked_command = user_id
        controllingGroup.save_to_table(table)

        message1 = "Currently supported annoyncement types:\nText message\nImage message"
        message2 = "Please enter annoyncement or type 'cancel' or 'Cancel' to cancel:"
        return linebot_utils.reply(event.reply_token,
                                   [message1, message2])

    if controllingGroup.waiting_for_input and user_id == controllingGroup.user_invoked_command:
        controllingGroup.waiting_for_input = False
        controllingGroup.user_invoked_command = ""
        controllingGroup.save_to_table(table)

        if isVideoMessage:
            return linebot_utils.reply(event.reply_token, ["Video messages are currently unsupported. Your annoyncement is cancelled!"])
        if isAudioMessage:
            return linebot_utils.reply(event.reply_token, ["Audio messages are currently unsupported. Your annoyncement is cancelled!"])
        if isFileMessage:
            return linebot_utils.reply(event.reply_token, ["Since line bots cannot send file messages, your annoyncement is cancelled!"])

        if isTextMessage and message.text.strip().lower() == "cancel":
            return linebot_utils.reply(event.reply_token, ["You cancelled an annoyncement."])
        if isTextMessage:
            message1 = message.text.strip()
            linebot_utils.push_text(
                controllingGroup.receiving_group_ids, [message1])

        if isImageMessage:
            file_path = linebot_utils.download_content_from_message_id(
                message.id)
            url = s3_utils.upload_to_s3(file_path)
            linebot_utils.push_image(controllingGroup.receiving_group_ids, url)

        message1 = "The following groups received annoyncement:"
        message2 = "\n".join(controllingGroup.receiving_group_names)
        return linebot_utils.reply(event.reply_token, [message1, message2])


@handler.add(JoinEvent)
def handle_join(event):
    import db_utils

    logger.info("> join event")

    if event.source.type != "group":
        return logger.warn("Event not came from group")

    group_id = event.source.group_id
    logger.info(f"group id: {group_id}")

    with ApiClient(linebot_utils.configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        group_summary = line_bot_api.get_group_summary(group_id)
    group_name = group_summary.group_name
    logger.info(f"group name: {group_name}")

    table = db_utils.get_table()
    item_count = table.scan()["Count"] # scan() returns real-time data
    joined_controlling_group = item_count == 0

    if joined_controlling_group:
        logger.info("> bot joined controlling group")

        db_utils.ControllingGroup(
            group_id, group_name).save_to_table(table)

        current_time = str(time.time())
        hashed_time = hashlib.sha256(current_time.encode()).hexdigest()
        generated_invitation_code = hashed_time[:4]

        message1 = \
            "Usage:\n"\
            "To make an annoyncement, type 'annoy' or 'Annoy' as a command in the group chat.\n"\
            "Wait for my reply and send a message as an annoyncement."
        message2 = \
            "Before making annoyncements, let's first configure the invite code for the dashboard.\n"\
            "Below is a randomly generated string that you can use as an invite code:"
        message3 = generated_invitation_code
        message4 = "Now, please enter something into the chat as an invite code:"
        return linebot_utils.reply(event.reply_token, [message1, message2, message3, message4])
    else:
        logger.info("> bot joined receiving group")

        DASHBOARD_URL = os.getenv('DASHBOARD_URL') or None
        if DASHBOARD_URL is None:
            logger.error("'DASHBOARD_URL' environment variable not found")
            exit(1)

        url_encoded_group_name = urllib.parse.quote(group_name)
        dashboard_url = f'{DASHBOARD_URL}?group_id={group_id}&group_name={url_encoded_group_name}'

        message1 = \
            "Annoyncement line bot is a self-hosted annoyncement system developed by VFLC.\n"\
            "For more information please visit https://github.com/BWsix/annoyncement-line-bot"
        message2 = \
            "For group admins to configure the annoyncement bot, please visit the link below:\n"\
            f"{dashboard_url}"
        return linebot_utils.reply(event.reply_token, [message1, message2])


# TODO: investigate the leave event
# @handler.add(LeaveEvent)
# def handle_leave(event):
#     logger.info("> leave event")
#
#     if event.source.type != "group":
#         return logger.warn("Event not came from group")
#
#     group_id = event.source.group_id
#     logger.info(f"group id: {group_id}")
#
#     with ApiClient(linebot_utils.configuration) as api_client:
#         line_bot_api = MessagingApi(api_client)
#         group_summary = line_bot_api.get_group_summary(group_id)
#     group_name = group_summary.group_name
#     logger.info(f"group name: {group_name}")
#
#     table = db_utils.get_table()
#     controllingGroup = db_utils.ControllingGroup.from_table(table)
#
#     receiving_group = db_utils.ReceivingGroup(group_id, group_name)
#     if receiving_group in controllingGroup.receiving_groups:
#         return logger.warn("Event not came from receiving group")
#
#     controllingGroup.receiving_groups.remove(receiving_group)
#     controllingGroup.save_to_table(table)
#
#     message1 = \
#         f"{receiving_group.group_name} kicked me out of their group."
#     return linebot_utils.push_text([controllingGroup.group_id], message1)


def lambda_update_webhook_url(event, _):
    logger.info("update webhook url")
    logger.info(event)
    linebot_utils.update_webhook_url(event['url'])


def lambda_handle_linebot(event, _):
    body = event['body']
    signature = event['headers']['x-line-signature']

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        return "Invalid signature. Please check your channel access token/channel secret."

    return 'ok'
