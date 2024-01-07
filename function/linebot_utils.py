import os
import typing
import tempfile
import hashlib
import logging

from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    ImageMessage,
    MessagingApi,
    MessagingApiBlob,
    PushMessageRequest,
    ReplyMessageRequest,
    SetWebhookEndpointRequest,
    TextMessage,
)

logger = logging.getLogger()
logger.level = logging.INFO


LINEBOT_ACCESS_TOKEN = os.getenv('LINEBOT_ACCESS_TOKEN')
LINEBOT_SECRET = os.getenv('LINEBOT_SECRET')

configuration = Configuration(access_token=LINEBOT_ACCESS_TOKEN)


def update_webhook_url(url: str):
    configuration = Configuration(access_token=LINEBOT_ACCESS_TOKEN)
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        req = SetWebhookEndpointRequest(endpoint=url)
        try:
            line_bot_api.set_webhook_endpoint(req)
            return "Okga"
        except Exception as e:
            print(e)
            return f"Error: {e}"


def push_text(group_ids: list[str], messages: list[str], silence=False):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        for group_id in group_ids:
            line_bot_api.push_message(PushMessageRequest(
                to=group_id,
                notificationDisabled=silence,
                customAggregationUnits=None,
                messages=[
                    TextMessage(
                        text=message.strip(),
                        quickReply=None,
                        quoteToken=None,
                    ) for message in messages
                ],
            ))
        return 'ok'


def download_content_from_message_id(message_id: str):
    logger.info(f"download_content_from_message_id(message_id: {message_id})")

    with ApiClient(configuration) as api_client:
        blob_api = MessagingApiBlob(api_client)
        content = blob_api.get_message_content(message_id)
    content_hash = hashlib.sha256(content).digest().hex()
    logger.info("Download succeeded")

    with tempfile.NamedTemporaryFile(dir="/tmp", delete=False) as f:
        f.write(content)
        tempfile_path = f.name
    logger.info(f"File saved to {tempfile_path}")

    dist_name = f"/tmp/{content_hash}.jpg"
    os.rename(tempfile_path, dist_name)
    logger.info(f"File renamed to {dist_name}")
    return dist_name


def push_image(group_ids: list[str], url: str, silence=False):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        for group_id in group_ids:
            line_bot_api.push_message(PushMessageRequest(
                to=group_id,
                notificationDisabled=silence,
                customAggregationUnits=None,
                messages=[ImageMessage(
                    quickReply=None,
                    originalContentUrl=url,
                    previewImageUrl=url,
                )],
            ))
        return 'ok'


# def push_video(group_ids: list[str], contentUrl: str, previewUrl: str, silence=False):
#     with ApiClient(configuration) as api_client:
#         line_bot_api = MessagingApi(api_client)
#
#         for group_id in group_ids:
#             line_bot_api.push_message(PushMessageRequest(
#                 to=group_id,
#                 notificationDisabled=silence,
#                 customAggregationUnits=None,
#                 messages=[VideoMessage(
#                     quickReply=None,
#                     trackingId=None,
#                     originalContentUrl=contentUrl,
#                     previewImageUrl=previewUrl,
#                 )],
#             ))
#         return 'ok'


# def push_audio(group_ids: list[str], contentUrl: str, duration: int, silence=False):
#     with ApiClient(configuration) as api_client:
#         line_bot_api = MessagingApi(api_client)
#
#         for group_id in group_ids:
#             line_bot_api.push_message(PushMessageRequest(
#                 to=group_id,
#                 notificationDisabled=silence,
#                 customAggregationUnits=None,
#                 messages=[AudioMessage(
#                     quickReply=None,
#                     originalContentUrl=contentUrl,
#                     duration=duration
#                 )],
#             ))
#         return 'ok'


def reply(reply_token: typing.Any, messages: list[str]):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        line_bot_api.reply_message(ReplyMessageRequest(
            replyToken=reply_token,
            notificationDisabled=False,
            messages=[
                TextMessage(
                    text=msg.strip(),
                    quickReply=None,
                    quoteToken=None,
                ) for msg in messages
            ],
        ))
        return 'ok'
