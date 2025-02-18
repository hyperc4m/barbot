import unittest
import datetime
from unittest.mock import patch

from barbot import schedule_util
from barbot.app import AppSettings
from barbot.database import ScheduledVenue

# March 2025
# S  M  T  W  T  F  S
#                   1
# 2  3  4  5  6  7  8
# 9  10 11 12 13 14 15
# 16 17 18 19 20 21 22
# 23 24 25 26 27 28 29
# 30 31

TEST_EVENTS = [
    ScheduledVenue('', 'foo', '0 19 ? * WED#4 *', duration_minutes=60 * 4)
]
TEST_APP_SETTINGS = AppSettings({
    'MAIN_EVENT_CRON': '0 19 ? * WED *',
    'MAIN_EVENT_DURATION': '4'
})



@patch('barbot.schedule_util.get_now')
class ScheduledEventActiveTest(unittest.TestCase):

    def test_returns_event_correctly_during_kickoff(self, mock_get_now):
        mock_get_now.side_effect = lambda tz: datetime.datetime(year=2025, month=3, day=24, hour=10, minute=0, second=0, tzinfo=tz)
        event = schedule_util.get_active_scheduled_event_inner(TEST_EVENTS, TEST_APP_SETTINGS)
        self.assertEqual(TEST_EVENTS[0], event)

    def test_returns_event_correctly_after_kickoff(self, mock_get_now):
        mock_get_now.side_effect = lambda tz: datetime.datetime(year=2025, month=3, day=25, hour=10, minute=0, second=0)
        event = schedule_util.get_active_scheduled_event_inner(TEST_EVENTS, TEST_APP_SETTINGS)
        self.assertEqual(TEST_EVENTS[0], event)

    def test_returns_none_correctly_week_before(self, mock_get_now):
        mock_get_now.side_effect = lambda tz: datetime.datetime(year=2025, month=3, day=17, hour=10, minute=0, second=0)
        event = schedule_util.get_active_scheduled_event_inner(TEST_EVENTS, TEST_APP_SETTINGS)
        self.assertIsNone(event)

    def test_returns_none_correctly_after_event(self, mock_get_now):
        mock_get_now.side_effect = lambda tz: datetime.datetime(year=2025, month=3, day=27, hour=10, minute=0, second=0)
        event = schedule_util.get_active_scheduled_event_inner(TEST_EVENTS, TEST_APP_SETTINGS)
        self.assertIsNone(event)