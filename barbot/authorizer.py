import os

from .app import AppSettings


def handle_auth(event, context):
    print(repr(event))
    app = AppSettings(os.environ)
    token = event.get('headers', {}).get('X-Telegram-Bot-Api-Secret-Token'.lower(), '')
    authorized = token == app.WEBHOOK_SECRET
    return {
      "isAuthorized": authorized,
      "context": {}
    }
