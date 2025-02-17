import unittest
from datetime import datetime
from unittest.mock import AsyncMock, ANY, MagicMock

import telegram

from barbot import webhook
from barbot.app import AppSettings
from barbot.bars import Bars


class MockServices(object):
    def __init__(self):
        db = MagicMock()
        db.return_value.get_current_poll_id.return_value = 1
        self.db = db

        bot = MagicMock()
        bot.return_value.stop_poll = AsyncMock()
        bot.return_value.send_message = AsyncMock()
        bot.return_value.pin_chat_message = AsyncMock()
        bot.return_value.get_chat_member = AsyncMock()
        bot.return_value.set_message_reaction = AsyncMock()
        self.bot = bot

        scheduler = MagicMock()
        self.scheduler = scheduler


class TestWebhookMessage(unittest.IsolatedAsyncioTestCase):
    async def test_reacts_with_success(self):
        mock_services = MockServices()
        app_settings = AppSettings({})
        bars = Bars(app_settings.BAR_SPREADSHEET)

        update = telegram.Update(
            update_id=1,
        )
        message = telegram.Message(
            message_id=2,
            date=datetime.utcnow(),
            text='Smuggler\'s Cove #barnight',
            chat=telegram.Chat(
                id=app_settings.MAIN_CHAT_ID,
                type=telegram.constants.ChatType.GROUP
            ),
            from_user=telegram.User(id=0, first_name='Ceres', is_bot=False)
        )

        await webhook.handle_message(update, message, mock_services.db(), mock_services.bot(), app_settings, bars)

        mock_services.bot.return_value.set_message_reaction.assert_called_with(
            chat_id=app_settings.MAIN_CHAT_ID,
            message_id=2,
            reaction=telegram.ReactionTypeEmoji(emoji="✍"),
            is_big=ANY
        )
