import asyncio
from typing import Mapping


class AppSettings(object):
    def __init__(self, env: Mapping[str, str]):
        self.MAIN_CHAT_ID = int(env.get('MAIN_CHAT_ID', '0'))
        self.TELEGRAM_BOT_TOKEN = env.get('TELEGRAM_BOT_TOKEN')
        self.WEBHOOK_SECRET = env.get('TELEGRAM_BOT_API_SECRET_TOKEN')
        self.DYNAMODB_ENDPOINT_URL = env.get('DYNAMODB_ENDPOINT_URL')
        self.DYNAMO_WEEK_TABLE_NAME = env.get('DYNAMO_WEEK_TABLE_NAME')
        self.BOT_USERNAME = env.get('BOT_USERNAME')
        self.WEBHOOK_URL = env.get('WEBHOOK_URL')
        self.SCHEDULE_GROUP_NAME = env.get('SCHEDULE_GROUP_NAME', '')
        self.CREATE_POLL_SCHEDULE_NAME = env.get('CREATE_POLL_SCHEDULE_NAME', '')
        self.CLOSE_POLL_SCHEDULE_NAME = env.get('CLOSE_POLL_SCHEDULE_NAME', '')
        self.BAR_SPREADSHEET = env.get('BAR_SPREADSHEET', '')
        self.SELENIUM_SERVER_URL = env.get('SELENIUM_SERVER_URL', 'http://localhost:4444')

        # If set, bar decision announcements will be sent to this chat_id instead of MAIN_CHAT_ID.
        self.ANNOUNCEMENT_CHAT_ID = env.get('ANNOUNCEMENT_CHAT_ID')


BARNIGHT_HASHTAG = '#barnight'

# This limit is imposed by the max number of poll options in a Telegram poll.\
# Change this if Telegram's limit changes in the future.
MAX_SUGGESTIONS = 10
MIN_VENUE_LENGTH = 1
MAX_VENUE_LENGTH = 100

asyncio_loop = asyncio.get_event_loop()
