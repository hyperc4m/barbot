import difflib
import json
import sys
import uuid
from typing import Dict, Any, Optional

import telegram

from . import database, app


bot = telegram.Bot(
    token=app.TELEGRAM_BOT_TOKEN
)


def error(message: str):
    sys.stderr.write(message)
    sys.stderr.write('\n')
    sys.stderr.flush()


def handle_webhook(event: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    body_json = event['body']
    body = json.loads(body_json)
    result = app.asyncio_loop.run_until_complete(handle_webhook_async(body))

    if result:
        return result

    return {}


async def handle_webhook_async(body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    print(f'Received webhook! {body}')

    update = telegram.Update.de_json(body, bot)
    if not update:
        error('Failed to parse Update body')
        return

    if update.inline_query is not None:
        return await handle_inline_query(update, update.inline_query)

    if update.chosen_inline_result is not None:
        await handle_chosen_inline_result(update, update.chosen_inline_result)

    if update.message is not None:
        await handle_message(update, update.message)


async def handle_inline_query(udpate: telegram.Update, query: telegram.InlineQuery) -> Optional[Dict[str, Any]]:
    # Make sure the user is part of the chatroom
    is_member = await database.is_user_part_of_main_chat(bot, user_id=query.from_user.id)

    query_text = query.query
    answers = []
    if query_text and is_member:
        current_suggestions = database.get_current_suggestions()
        possibilities = [x.venue for x in current_suggestions]
        suggestions_by_name = {s.venue: s for s in current_suggestions}
        matches = difflib.get_close_matches(query_text, possibilities, n=5, cutoff=0.1)

        # if query_text not in matches:
        #     matches.insert(0, query_text)

        def make_result(hex_uuid: str, match_name: str) -> Dict[str, Any]:
            return {
                'type': 'article',
                'id': hex_uuid,
                'title': match_name,
                'input_message_content': {
                    'message_text': f'{match_name} #barnight'
                }
            }

        if query_text not in suggestions_by_name:
            answers.append(make_result('null', query_text))
        answers.extend(make_result(suggestions_by_name[x].uuid, x) for x in matches)

    print(f'returning {len(answers)} answers')

    return {
        'method': 'answerInlineQuery',
        'inline_query_id': query.id,
        'results': answers,
        'cache_time': 60,
        'is_personal': True  # Needs to be personal so that we don't leak suggestions to non-members.
    }


async def add_suggestion(venue: str, user_id: int, username: str):

    suggestions = database.get_current_suggestions(bypass_cache=True)

    found_suggestion: Optional[database.Suggestion] = None
    for suggestion in suggestions:
        if suggestion.venue.lower() == venue.lower():
            found_suggestion = suggestion
            break

    if found_suggestion is not None:
        await bot.send_message(
            chat_id=app.MAIN_CHAT_ID,
            text=f'@{username} has suggested "{venue}" for #barnight, '
                 f'which was already suggested by {found_suggestion.user_handle}'
        )
    else:
        venue_uuid = uuid.uuid4().hex
        database.add_suggestion(venue_uuid, venue, user_id, username)
        # Send message to the main chat to let people know that a suggestion was added.
        await bot.send_message(
            chat_id=app.MAIN_CHAT_ID,
            text=f'@{username} has successfully suggested "{venue}" for #barnight'
        )


async def handle_chosen_inline_result(update: telegram.Update, result: telegram.ChosenInlineResult):
    if not await database.is_user_part_of_main_chat(bot, result.from_user.id):
        return

    venue: str
    if result.result_id == 'null':
        venue = result.query
    else:
        venue = database.get_suggestion_by_uuid(result.result_id).venue

    await add_suggestion(venue, result.from_user.id, result.from_user.username)
    #
    #
    #     venue_uuid = uuid.uuid4().hex
    #     database.add_suggestion(venue_uuid, venue, result.from_user.id, result.from_user.username)
    #     # Send message to the main chat to let people know that a suggestion was added.
    #     await update.get_bot().send_message(
    #         chat_id=app.MAIN_CHAT_ID,
    #         text=f'@{result.from_user.username} has successfully suggested "{venue}" for #barnight'
    #     )
    # else:
    #
    #     await update.get_bot().send_message(
    #         chat_id=app.MAIN_CHAT_ID,
    #         text=f'@{result.from_user.username} has suggested "{suggestion.venue}" for #barnight, '
    #              f'which was already suggested by {suggestion.user_handle}'
    #     )


async def handle_message(update: telegram.Update, message: telegram.Message):
    is_admin = await database.get_user_status_in_main_chat(bot, message.from_user.id)

    if message.chat.type == telegram.Chat.PRIVATE:
        if message.text.lower().startswith('/start'):
            message_text = f'Hello there! You can use me to suggest venues for bar night!\n\n' \
                    f'To send a venue suggestion, send a message to the main chatroom with the hashtag #barnight. ' \
                    f'You can also use @{app.BOT_USERNAME} in your message to suggest a venue.'
            await bot.send_message(
                message.chat.id,
                message_text
            )
    elif message.chat.id == app.MAIN_CHAT_ID:
        if '#barnight' in message.text.lower():
            text_without_hashtag = message.text.lower().replace('#barnight', '').strip()
            await add_suggestion(text_without_hashtag.title(), message.from_user.id, message.from_user.username)
