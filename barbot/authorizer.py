import os

from . import app


def handle_auth(event, context):
    print(repr(event))
    token = event.get('headers', {}).get('X-Telegram-Bot-Api-Secret-Token'.lower(), '')
    authorized = token == app.WEBHOOK_SECRET
    return {
      "isAuthorized": authorized,
      "context": {}
    }
