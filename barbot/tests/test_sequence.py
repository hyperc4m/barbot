import datetime
import unittest
from typing import Sequence, Dict
from unittest.mock import AsyncMock, ANY, MagicMock, patch

import telegram

from barbot import sequence
from barbot.app import AppSettings
from barbot.database import ScheduledVenue, Suggestion
from barbot.sequence import SequenceServices


class TestSchedule(object):
    def __init__(self):
        self.create_poll = '0 20 ? * MON *'
        self.close_poll = '0 20 ? * TUE *'

    def configure_scheduler_and_app(self, scheduler: MagicMock, app: AppSettings):
        timezone_name = 'America/Los_Angeles'
        app.CREATE_POLL_SCHEDULE_NAME = 'CREATE_POLL'
        app.CLOSE_POLL_SCHEDULE_NAME = 'CLOSE_POLL'
        schedules = {
            app.CREATE_POLL_SCHEDULE_NAME: self.create_poll,
            app.CLOSE_POLL_SCHEDULE_NAME: self.close_poll
        }

        app.MAIN_EVENT_CRON = '0 19 ? * WED *'
        app.MAIN_EVENT_TIMEZONE = 'America/Los_Angeles'

        def get_schedule(*, Name, GroupName) -> Dict[str, str]:
            return { 'ScheduleExpression': schedules[Name], 'ScheduleExpressionTimezone': timezone_name }

        scheduler.return_value.get_schedule.side_effect = get_schedule

class MockServices(object):
    def __init__(self):
        db = MagicMock()
        db.return_value.get_current_poll_id.return_value = 1
        self.db = db

        bot = MagicMock()
        bot.return_value.stop_poll = AsyncMock()
        bot.return_value.send_message = AsyncMock()
        bot.return_value.send_poll = AsyncMock()
        bot.return_value.pin_chat_message = AsyncMock()
        self.bot = bot

        scheduler = MagicMock()
        self.scheduler = scheduler

        self.app_settings = AppSettings({})

    def configure_schedule_and_time(self, schedule: TestSchedule, mock_get_now, now: datetime.datetime):
        schedule.configure_scheduler_and_app(self.scheduler, self.app_settings)
        mock_get_now.side_effect = lambda tz: now.replace(tzinfo=tz)

    def configure_stop_poll(self, options: Sequence[telegram.PollOption]):
        self.bot.return_value.stop_poll.return_value = telegram.Poll(
            id='1',
            question='',
            options=options,
            total_voter_count=0,
            is_closed=True,
            is_anonymous=False,
            type='',
            allows_multiple_answers=True
        )

    def make_services(self) -> SequenceServices:
        return SequenceServices(self.db(), self.bot(), self.scheduler(), self.app_settings)


@patch('barbot.schedule_util.get_now')
class TestAskForSuggestions(unittest.IsolatedAsyncioTestCase):
    async def test_message_sent_when_scheduled_event_doesnt_conflict(self, mock_get_now):
        mock_services = MockServices()
        mock_services.db.return_value.get_scheduled_venues.return_value = [
            ScheduledVenue('', 'El Rio', '0 19 ? * WED#4 *', 4)
        ]
        mock_services.configure_schedule_and_time(TestSchedule(), mock_get_now, datetime.datetime(year=2025, month=3, day=17, hour=10))

        result = await sequence.handle_ask_for_suggestions({}, mock_services.make_services())

        expected_message = 'It\'s time for bar night suggestions! Message @None or end a message with #barnight to input a suggestion!'
        mock_services.bot.return_value.send_message.assert_called_with(
            chat_id=ANY, text=expected_message)


    async def test_scheduled_event_announced_correctly(self, mock_get_now):
        mock_services = MockServices()
        mock_services.db.return_value.get_scheduled_venues.return_value = [
            ScheduledVenue('', 'El Rio', '0 19 ? * WED#4 *', 4)
        ]
        mock_services.configure_schedule_and_time(TestSchedule(), mock_get_now,
                                                  datetime.datetime(year=2025, month=3, day=24, hour=10))

        result = await sequence.handle_ask_for_suggestions({}, mock_services.make_services())

        expected_message = 'Next bar night will be at *El Rio*\\!'
        mock_services.bot.return_value.send_message.assert_called_with(
            chat_id=ANY, text=expected_message, parse_mode='MarkdownV2',
            disable_web_page_preview=ANY, reply_to_message_id=ANY)


@patch('barbot.schedule_util.get_now')
class TestCreatePoll(unittest.IsolatedAsyncioTestCase):
    async def test_usual_flow_poll_created(self, mock_get_now):
        mock_services = MockServices()
        mock_services.db.return_value.get_scheduled_venues.return_value = [
            ScheduledVenue('', 'El Rio', '0 19 ? * WED#4 *', 4)
        ]
        mock_services.db.return_value.get_current_suggestions.return_value = [
            Suggestion('', 'Foo', 0, ''),
            Suggestion('', 'Bar', 0, '')
        ]
        mock_services.configure_schedule_and_time(TestSchedule(), mock_get_now,
                                                  datetime.datetime(year=2025, month=3, day=17, hour=10))

        result = await sequence.handle_create_poll({}, mock_services.make_services())

        mock_services.bot.return_value.send_message.assert_not_called()
        mock_services.bot.return_value.send_poll.assert_called_with(
            chat_id=mock_services.app_settings.MAIN_CHAT_ID, question=ANY,
            options=['Foo', 'Bar'],
            is_anonymous=False, type='regular', allows_multiple_answers=True
        )
        mock_services.bot.return_value.pin_chat_message.assert_called_with(
            chat_id=mock_services.app_settings.MAIN_CHAT_ID, message_id=ANY)

    async def test_no_poll_created_during_special_event(self, mock_get_now):
        mock_services = MockServices()
        mock_services.db.return_value.get_scheduled_venues.return_value = [
            ScheduledVenue('', 'El Rio', '0 19 ? * WED#4 *', 4)
        ]
        mock_services.configure_schedule_and_time(TestSchedule(), mock_get_now,
                                                  datetime.datetime(year=2025, month=3, day=24, hour=10))

        result = await sequence.handle_create_poll({}, mock_services.make_services())

        mock_services.bot.return_value.send_message.assert_not_called()
        mock_services.bot.return_value.send_poll.assert_not_called()
        mock_services.bot.return_value.pin_chat_message.assert_not_called()


@patch('barbot.schedule_util.get_now')
class TestPollReminder(unittest.IsolatedAsyncioTestCase):
    async def test_usual_flow_reminder_sent(self, mock_get_now):
        mock_services = MockServices()
        mock_services.db.return_value.get_scheduled_venues.return_value = [
            ScheduledVenue('', 'El Rio', '0 19 ? * WED#4 *', 4)
        ]
        mock_services.configure_schedule_and_time(TestSchedule(), mock_get_now,
                                                  datetime.datetime(year=2025, month=3, day=17, hour=10))

        result = await sequence.handle_poll_reminder({}, mock_services.make_services())

        mock_services.bot.return_value.send_message.assert_called_with(
            chat_id=mock_services.app_settings.MAIN_CHAT_ID,
            text='REMINDER: Don\'t forget to vote!', reply_to_message_id=ANY)

    async def test_no_reminder_sent_during_special_event(self, mock_get_now):
        mock_services = MockServices()
        mock_services.db.return_value.get_scheduled_venues.return_value = [
            ScheduledVenue('', 'El Rio', '0 19 ? * WED#4 *', 4)
        ]
        mock_services.configure_schedule_and_time(TestSchedule(), mock_get_now,
                                                  datetime.datetime(year=2025, month=3, day=24, hour=10))

        result = await sequence.handle_poll_reminder({}, mock_services.make_services())

        mock_services.bot.return_value.send_message.assert_not_called()


class TestChooseWinner(unittest.IsolatedAsyncioTestCase):
    async def test_typical_bar(self):
        mock_services = MockServices()
        mock_services.configure_stop_poll([
            telegram.PollOption('Foo', 5),
            telegram.PollOption('Bar', 6),  # pun intended
        ])

        result = await sequence.handle_choose_winner({}, mock_services.make_services())

        expected_message = 'Calling it for *Bar*\\!'
        mock_services.bot.return_value.send_message.assert_called_with(
            chat_id=ANY, text=expected_message, parse_mode='MarkdownV2',
            disable_web_page_preview=ANY, reply_to_message_id=ANY)

    async def test_bar_with_markdown_characters(self):
        mock_services = MockServices()
        mock_services.configure_stop_poll([
            telegram.PollOption('Foo', 5),
            telegram.PollOption('Din.gles', 6),
        ])

        result = await sequence.handle_choose_winner({}, mock_services.make_services())
        expected_message = 'Calling it for *Din\\.gles*\\!'
        mock_services.bot.return_value.send_message.assert_called_with(
            chat_id=ANY, text=expected_message, parse_mode='MarkdownV2',
            disable_web_page_preview=ANY, reply_to_message_id=ANY)

    async def test_bar_ending_with_punctuation(self):
        punctuation_marks = ['.', '!', '?']
        for punctuation_mark in punctuation_marks:
            mock_services = MockServices()
            mock_services.configure_stop_poll([
                telegram.PollOption('Foo', 5),
                telegram.PollOption(f'Dingles{punctuation_mark}', 6),
            ])

            result = await sequence.handle_choose_winner({}, mock_services.make_services())
            expected_message = 'Calling it for *Dingles*\\!'
            mock_services.bot.return_value.send_message.assert_called_with(
                chat_id=ANY, text=expected_message, parse_mode='MarkdownV2',
                disable_web_page_preview=ANY, reply_to_message_id=ANY)

    async def test_result_sent_to_associated_channel(self):
        mock_services = MockServices()
        mock_services.configure_stop_poll([
            telegram.PollOption('Foo', 5),
            telegram.PollOption(f'Dingles', 6),
        ])
        mock_services.app_settings.MAIN_CHAT_ID = 12345
        mock_services.app_settings.ANNOUNCEMENT_CHAT_ID = 67890

        result = await sequence.handle_choose_winner({}, mock_services.make_services())

        expected_message = 'The next bar night will be held at Dingles\\.'
        mock_services.bot.return_value.send_message.assert_called_with(
            chat_id=mock_services.app_settings.ANNOUNCEMENT_CHAT_ID, text=ANY, parse_mode=ANY,
            disable_web_page_preview=ANY, reply_to_message_id=ANY)
        mock_services.bot.return_value.pin_chat_message.assert_not_called()


    async def test_result_sent_to_main_group_if_associated_channel_not_set(self):
        mock_services = MockServices()
        mock_services.configure_stop_poll([
            telegram.PollOption('Foo', 5),
            telegram.PollOption(f'Dingles', 6),
        ])
        mock_services.app_settings.MAIN_CHAT_ID = 12345

        result = await sequence.handle_choose_winner({}, mock_services.make_services())

        expected_message = 'Calling it for *Dingles*\\!'
        mock_services.bot.return_value.send_message.assert_called_with(
            chat_id=mock_services.app_settings.MAIN_CHAT_ID, text=expected_message, parse_mode=ANY,
            disable_web_page_preview=ANY, reply_to_message_id=ANY)
        mock_services.bot.return_value.pin_chat_message.assert_called_with(
            chat_id=mock_services.app_settings.MAIN_CHAT_ID, message_id=ANY)


    @patch('barbot.schedule_util.get_now')
    async def test_noop_when_scheduled_event_conflicts(self, mock_get_now):
        mock_services = MockServices()
        mock_services.configure_stop_poll([
            telegram.PollOption('Foo', 5),
            telegram.PollOption(f'Dingles', 6),
        ])
        mock_services.app_settings.MAIN_CHAT_ID = 12345
        mock_services.db.return_value.get_scheduled_venues.return_value = [
            ScheduledVenue('', 'El Rio', '0 19 ? * WED#4 *', 4)
        ]
        mock_services.app_settings.MAIN_EVENT_CRON = '0 19 ? * WED *'
        mock_services.app_settings.MAIN_EVENT_TIMEZONE = 'America/Los_Angeles'
        mock_get_now.side_effect = lambda tz: datetime.datetime(year=2025, month=3, day=24, hour=10, tzinfo=tz)

        result = await sequence.handle_choose_winner({}, mock_services.make_services())

        mock_services.bot.return_value.send_message.assert_not_called()

    @patch('barbot.schedule_util.get_now')
    async def test_result_announced_when_scheduled_event_doesnt_conflict(self, mock_get_now):
        mock_services = MockServices()
        mock_services.configure_stop_poll([
            telegram.PollOption('Foo', 5),
            telegram.PollOption(f'Dingles', 6),
        ])
        mock_services.app_settings.MAIN_CHAT_ID = 12345
        mock_services.db.return_value.get_scheduled_venues.return_value = [
            ScheduledVenue('', 'El Rio', '0 19 ? * WED#4 *', 4)
        ]
        mock_services.app_settings.MAIN_EVENT_CRON = '0 19 ? * WED *'
        mock_services.app_settings.MAIN_EVENT_TIMEZONE = 'America/Los_Angeles'
        mock_get_now.side_effect = lambda tz: datetime.datetime(year=2025, month=3, day=17, hour=10, tzinfo=tz)

        result = await sequence.handle_choose_winner({}, mock_services.make_services())

        expected_message = 'Calling it for *Dingles*\\!'
        mock_services.bot.return_value.send_message.assert_called_with(
            chat_id=mock_services.app_settings.MAIN_CHAT_ID, text=expected_message, parse_mode=ANY,
            disable_web_page_preview=ANY, reply_to_message_id=ANY)
        mock_services.bot.return_value.pin_chat_message.assert_called_with(
            chat_id=mock_services.app_settings.MAIN_CHAT_ID, message_id=ANY)