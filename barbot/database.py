import abc
import datetime
from typing import List, Optional, Dict, Any, Tuple

import boto3
import telegram

from .app import AppSettings, MAX_SUGGESTIONS

CACHE_TTL = datetime.timedelta(seconds=3)


class Suggestion(object):
    def __init__(self, hex_uuid: str, venue: str, user_id: int, user_handle: str):
        self.uuid = hex_uuid
        self.venue = venue
        self.user_id = user_id
        self.user_handle = user_handle


class ScheduledVenue(object):
    def __init__(self, hex_uuid: str, venue_name: str, cron: str, duration_minutes: int):
        self.uuid = hex_uuid
        self.venue_name = venue_name
        self.cron = cron
        self.duration_minutes = duration_minutes


last_suggestions_update_time = datetime.datetime(day=1, month=1, year=1)
cached_suggestions: List[Suggestion] = []

def make_suggestion(k: str, v: Dict[str, Any]) -> Suggestion:
    m = v['M']
    return Suggestion(k, m['name']['S'], int(m['user_id']['N']), m['user_handle']['S'])

def make_scheduled_venue(k: str, v: Dict[str, Any]) -> ScheduledVenue:
    m = v['M']
    return ScheduledVenue(k, m['venue_name']['S'], m['cron']['S'], int(m['duration_minutes']['N']))


class Database(abc.ABC):
    @abc.abstractmethod
    def get_current_poll_id(self) -> int:
        pass

    @abc.abstractmethod
    def set_current_poll_id(self, poll_id: int) -> None:
        pass

    @abc.abstractmethod
    def get_current_suggestions(self, bypass_cache=False) -> List[Suggestion]:
        pass

    @abc.abstractmethod
    def get_suggestion_by_uuid(self, hex_uuid: str) -> Optional[Suggestion]:
        pass

    @abc.abstractmethod
    def clear_suggestions(self) -> None:
        pass

    @abc.abstractmethod
    def add_suggestion(self, hex_uuid: str, venue: str, user_id: int, user_handle: str):
        pass

    @abc.abstractmethod
    def remove_suggestion(self, hex_uuid: str):
        pass

    @abc.abstractmethod
    def add_scheduled_venue(self, hex_uuid: str, venue_name: str, cron: str, duration_minutes: int) -> None:
        pass

    @abc.abstractmethod
    def remove_scheduled_venue(self, hex_uuid: str) -> None:
        pass

    @abc.abstractmethod
    def get_scheduled_venues(self) -> List[ScheduledVenue]:
        pass


class DynamoDatabase(Database):
    def __init__(self, app: AppSettings):
        self.app = app
        if app.DYNAMODB_ENDPOINT_URL:
            self.dynamodb = boto3.client('dynamodb', endpoint_url=app.DYNAMODB_ENDPOINT_URL)
        else:
            self.dynamodb = boto3.client('dynamodb')

    def get_current_poll_id(self) -> int:
        result = self.dynamodb.get_item(
            TableName=self.app.DYNAMO_WEEK_TABLE_NAME,
            Key={'id': {'S': 'current'}},
            ConsistentRead=True
        )
        item = result.get('Item', {})
        return int(item.get('poll_id', {}).get('N', 0))


    def set_current_poll_id(self, poll_id: int) -> None:
        self.dynamodb.update_item(
            TableName=self.app.DYNAMO_WEEK_TABLE_NAME,
            Key={'id': {'S': 'current'}},
            UpdateExpression='SET poll_id = :p',
            ExpressionAttributeValues={
                ':p': {'N': str(poll_id)}
            }
        )

    def get_current_suggestions(self, bypass_cache=False) -> List[Suggestion]:
        global cached_suggestions
        global last_suggestions_update_time
        now = datetime.datetime.utcnow()
        if not bypass_cache and now < last_suggestions_update_time + CACHE_TTL:
            return cached_suggestions

        get_result = self.dynamodb.get_item(
            TableName=self.app.DYNAMO_WEEK_TABLE_NAME,
            Key={'id': {'S': 'current'}}
        )
        item = get_result.get('Item')
        if not item:
            return []
        suggestions_map = item['venues']['M']
        suggestions = [make_suggestion(k, v) for k, v in suggestions_map.items()]
        cached_suggestions = suggestions
        last_suggestions_update_time = now
        return suggestions


    def get_suggestion_by_uuid(self, hex_uuid: str) -> Optional[Suggestion]:
        get_result = self.dynamodb.get_item(
            TableName=self.app.DYNAMO_WEEK_TABLE_NAME,
            Key={'id': {'S': 'current'}},
        )
        venue_data = get_result.get('Item', {}).get('venues', {}).get('M', {}).get(hex_uuid)
        if not venue_data:
            return None
        return make_suggestion(hex_uuid, venue_data)


    def clear_suggestions(self) -> None:
        global cached_suggestions
        global last_suggestions_update_time
        self.dynamodb.update_item(
            TableName=self.app.DYNAMO_WEEK_TABLE_NAME,
            Key={'id': {'S': 'current'}},
            UpdateExpression="SET venues = :empty",
            ExpressionAttributeValues={
                ':empty': {'M': {}}
            }
        )
        cached_suggestions.clear()
        last_suggestions_update_time = datetime.datetime.utcnow()


    def add_suggestion(self, hex_uuid: str, venue: str, user_id: int, user_handle: str):
        cached_suggestions.append(Suggestion(hex_uuid, venue, user_id, user_handle))

        self.dynamodb.update_item(
            TableName=self.app.DYNAMO_WEEK_TABLE_NAME,
            Key={'id': {'S': 'current'}},
            UpdateExpression='SET venues.#uuid = :value',
            ConditionExpression='size(venues) < :max_suggestions',
            ExpressionAttributeNames={
                '#uuid': hex_uuid
            },
            ExpressionAttributeValues={
                ':value': {'M': {
                    'name': {'S': venue},
                    'user_id': {'N': str(user_id)},
                    'user_handle': {'S': user_handle}
                }},
                ':max_suggestions': {'N': str(MAX_SUGGESTIONS)}
            }
        )


    def remove_suggestion(self, hex_uuid: str):
        self.dynamodb.update_item(
            TableName=self.app.DYNAMO_WEEK_TABLE_NAME,
            Key={'id': {'S': 'current'}},
            UpdateExpression='REMOVE venues.#uuid',
            ExpressionAttributeNames={
                '#uuid': hex_uuid
            }
        )
        # Invalidate the cache
        global last_suggestions_update_time
        last_suggestions_update_time = datetime.datetime(day=1, month=1, year=1)

    def add_scheduled_venue(self, hex_uuid: str, venue_name: str, cron: str, duration_minutes: int) -> None:
        self.dynamodb.update_item(
            TableName=self.app.DYNAMO_EVENTS_TABLE_NAME,
            Key={'id': {'S': 'current'}},
            UpdateExpression='SET events.#uuid = :value',
            ExpressionAttributeNames={
                '#uuid': hex_uuid
            },
            ExpressionAttributeValues={
                ':value': {'M': {
                    'venue_name': {'S': venue_name},
                    'cron': {'S': cron},
                    'duration_minutes': {'N': str(duration_minutes)}
                }}
            }
        )

    def remove_scheduled_venue(self, hex_uuid: str) -> None:
        self.dynamodb.update_item(
            TableName=self.app.DYNAMO_EVENTS_TABLE_NAME,
            Key={'id': {'S': 'current'}},
            UpdateExpression='REMOVE events.#uuid',
            ExpressionAttributeNames={
                '#uuid': hex_uuid
            }
        )

    def get_scheduled_venues(self) -> List[ScheduledVenue]:
        get_result = self.dynamodb.get_item(
            TableName=self.app.DYNAMO_EVENTS_TABLE_NAME,
            Key={'id': {'S': 'current'}}
        )
        item = get_result.get('Item')
        if not item:
            return []

        events_map = item['events']['M']
        scheduled_venues = [make_scheduled_venue(k, v) for k, v in events_map.items()]
        return scheduled_venues


cached_membership: Dict[int, Tuple[str, datetime.datetime]] = {}


async def get_user_status_in_main_chat(bot: telegram.Bot, app: AppSettings, user_id: int) -> str:
    now = datetime.datetime.utcnow()

    cached_result = cached_membership.get(user_id)
    if cached_result is not None:
        status, last_lookup = cached_result
        if last_lookup + CACHE_TTL > now:
            # cached result is still valid.
            return status

    result = await bot.get_chat_member(
        chat_id=app.MAIN_CHAT_ID,
        user_id=user_id
    )

    print(f'User status of user id {user_id} is {result.status}')

    cached_membership[user_id] = (result.status, now)
    return result.status


async def is_user_part_of_main_chat(bot: telegram.Bot, app: AppSettings, user_id: int) -> bool:
    status = await get_user_status_in_main_chat(bot, app, user_id)
    return status in (telegram.ChatMember.OWNER, telegram.ChatMember.ADMINISTRATOR,
                      telegram.ChatMember.MEMBER, telegram.ChatMember.RESTRICTED)


async def is_user_admin_of_main_chat(bot: telegram.Bot, app: AppSettings, user_id: int) -> bool:
    status = await get_user_status_in_main_chat(bot, app, user_id)
    return status in (telegram.ChatMember.OWNER, telegram.ChatMember.ADMINISTRATOR)
