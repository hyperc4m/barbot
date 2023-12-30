import datetime
import traceback

import croniter
import dateutil.tz
import re
from typing import Optional

import boto3

from . import app


scheduler = boto3.client('scheduler')


cron_regex = re.compile(r'cron\((.*)\)')


def get_schedule_time(schedule_name: str) -> Optional[str]:
    try:
        result = scheduler.get_schedule(
            GroupName=app.SCHEDULE_GROUP_NAME,
            Name=schedule_name
        )
    except:
        traceback.print_exc()
        return None

    expression = result.get('ScheduleExpression', '')
    expression_timezone = result.get('ScheduleExpressionTimezone', '')

    match = cron_regex.match(expression)
    if not match:
        return None

    cron_str = match.group(1).strip()

    tz = dateutil.tz.gettz(expression_timezone)
    base = datetime.datetime.now(tz)
    cron = croniter.croniter(cron_str, base)

    next_time = next(cron, None)
    if not next_time:
        return None

    return next_time.strftime('%A at %I:%M%p')
