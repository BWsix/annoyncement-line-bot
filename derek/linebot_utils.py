import os
import typing

from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    PushMessageRequest,
    ReplyMessageRequest,
    TextMessage,
)


LINEBOT_ACCESS_TOKEN = os.getenv('LINEBOT_ACCESS_TOKEN')
LINEBOT_SECRET = os.getenv('LINEBOT_SECRET')

configuration = Configuration(access_token=LINEBOT_ACCESS_TOKEN)


def push_text(group_ids: list[str], message: str, silence=False):
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
                    )
                ],
            ))
        return 'ok'


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
