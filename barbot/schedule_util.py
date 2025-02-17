import calendar
import datetime
import traceback

import croniter
import dateutil.tz
import re
from typing import Optional, List, Tuple
from mypy_boto3_scheduler import EventBridgeSchedulerClient

import boto3

from barbot.app import AppSettings
from barbot.database import ScheduledVenue, Database


def make_scheduler() -> EventBridgeSchedulerClient:
    return boto3.client('scheduler')


cron_regex = re.compile(r'cron\(\s*(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*\)')


def get_now(tz: datetime.tzinfo) -> datetime.datetime:
    """This function can be mocked in tests."""
    return datetime.datetime.now(tz)

def get_schedule_cron(scheduler: EventBridgeSchedulerClient, app: AppSettings, schedule_name: str) -> Tuple[str, datetime.tzinfo]:
    result = scheduler.get_schedule(
        GroupName=app.SCHEDULE_GROUP_NAME,
        Name=schedule_name
    )

    expression = result.get('ScheduleExpression', '')
    expression_timezone = result.get('ScheduleExpressionTimezone', '')

    tz = dateutil.tz.gettz(expression_timezone)
    return expression, tz


def get_schedule_time(scheduler: EventBridgeSchedulerClient, app: AppSettings, schedule_name: str) -> Optional[str]:
    expression, tz = get_schedule_cron(scheduler, app, schedule_name)
    base = get_now(tz)
    next_time = get_next_cron(expression, base)
    if next_time is None:
        return None
    return next_time.strftime('%A at %I:%M%p')


def get_next_cron(expression: str, start_time: datetime.datetime) -> Optional[datetime.datetime]:
    match = cron_regex.match(expression)
    # TODO: If it's malformed, shouldn't we throw?
    if not match:
        return None

    minutes = match.group(1)
    hours = match.group(2)
    day_of_month = match.group(3)
    if day_of_month == '?':
        day_of_month = '*'
    month = match.group(4)
    day_of_week = match.group(5)
    year = match.group(6)

    cron_str = f'{minutes} {hours} {day_of_month} {month} {day_of_week}'
    cron = croniter.croniter(cron_str, start_time)
    return cron.get_next(datetime.datetime)

def get_active_scheduled_event(db: Database, app: AppSettings) -> Optional[ScheduledVenue]:
    events = db.get_scheduled_venues()
    return get_active_scheduled_event_inner(events, app)

def get_active_scheduled_event_inner(events: List[ScheduledVenue], app: AppSettings) -> Optional[ScheduledVenue]:
    tz = dateutil.tz.gettz(app.MAIN_EVENT_TIMEZONE)
    now = get_now(tz)

    next_main_event = get_next_cron(f'cron({app.MAIN_EVENT_CRON})', now)

    if next_main_event is None:
        return None

    main_event_end = next_main_event + datetime.timedelta(hours=app.MAIN_EVENT_DURATION_HOURS)

    for event in events:
        next_scheduled_event = get_next_cron(f'cron({event.cron})', now)
        if next_scheduled_event is None:
            continue

        next_scheduled_event_end = next_scheduled_event + datetime.timedelta(hours=event.duration_hours)

        # Does this event overlap with the main event?
        if main_event_end > next_scheduled_event and next_main_event < next_scheduled_event_end:
            return event

    return None
