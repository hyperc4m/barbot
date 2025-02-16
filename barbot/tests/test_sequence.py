import unittest
from unittest.mock import AsyncMock, ANY, MagicMock

import telegram

from barbot import sequence
from barbot.sequence import SequenceServices


class MockServices(object):
    def __init__(self):
        db = MagicMock()
        db.return_value.get_current_poll_id.return_value = 1
        self.db = db

        bot = MagicMock()
        bot.return_value.stop_poll = AsyncMock()
        bot.return_value.send_message = AsyncMock()
        bot.return_value.pin_chat_message = AsyncMock()
        bot.return_value.stop_poll.return_value = telegram.Poll(
            id='1',
            question='',
            options=[
                telegram.PollOption('Foo', 5),
                telegram.PollOption('Bar', 6),  # pun intended
            ],
            total_voter_count=0,
            is_closed=True,
            is_anonymous=False,
            type='',
            allows_multiple_answers=True
        )
        self.bot = bot

        scheduler = MagicMock()
        self.scheduler = scheduler

    def make_services(self) -> SequenceServices:
        return SequenceServices(self.db(), self.bot(), self.scheduler())


class TestChooseWinner(unittest.IsolatedAsyncioTestCase):
    async def test_typical_bar(self):
        mock_services = MockServices()

        result = await sequence.handle_choose_winner({}, mock_services.make_services())

        expected_message = 'Calling it for *Bar*\\!'
        mock_services.bot.return_value.send_message.assert_called_with(
            chat_id=ANY, text=expected_message, parse_mode='MarkdownV2',
            disable_web_page_preview=ANY, reply_to_message_id=ANY)
