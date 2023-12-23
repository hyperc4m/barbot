import asyncio
import os


MAIN_CHAT_ID = os.environ.get('MAIN_CHAT_ID')
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
WEBHOOK_SECRET = os.environ.get('TELEGRAM_BOT_API_SECRET_TOKEN')
DYNAMO_WEEK_TABLE_NAME = os.environ.get('DYNAMO_WEEK_TABLE_NAME')
BOT_USERNAME = os.environ.get('BOT_USERNAME')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')

asyncio_loop = asyncio.get_event_loop()
