import difflib
import json
import re
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
                    'message_text': f'{match_name} {app.BARNIGHT_HASHTAG}'
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


async def add_suggestion(venue: str, user_id: int, username: str) -> None:
    venue = re.sub(r'\s+', ' ', venue).strip().lower().capitalize()
    venue = re.sub(r'\s\S', lambda m: m.group(0).title(), venue)
    venue = venue[:256]

    suggestions = database.get_current_suggestions(bypass_cache=True)

    found_suggestion: Optional[database.Suggestion] = None

    normalized_venue = [c.lower() for c in venue if c.isalpha()]

    for suggestion in suggestions:
        normalized_suggestion_venue = [c.lower() for c in suggestion.venue if c.isalpha()]
        if normalized_venue == normalized_suggestion_venue:
            found_suggestion = suggestion
            break

    if found_suggestion is not None:
        await bot.send_message(
            chat_id=app.MAIN_CHAT_ID,
            text=f'@{username} has suggested "{venue}" for {app.BARNIGHT_HASHTAG}, '
                 f'which was already suggested by {found_suggestion.user_handle}'
        )
    else:
        venue_uuid = uuid.uuid4().hex
        database.add_suggestion(venue_uuid, venue, user_id, username)
        # Send message to the main chat to let people know that a suggestion was added.
        await bot.send_message(
            chat_id=app.MAIN_CHAT_ID,
            text=f'@{username} has successfully suggested "{venue}" for {app.BARNIGHT_HASHTAG}'
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
    # Don't accept input from other bots.
    if message.from_user.is_bot:
        return

    # Only accept messages with text.
    if not message.text:
        return

    is_admin = await database.get_user_status_in_main_chat(bot, message.from_user.id)

    message_lower = message.text.lower()

    if message.chat.type == telegram.Chat.PRIVATE:
        if message_lower.startswith('/start'):
            message_text = f'Hello there! You can use me to suggest venues for bar night!\n\n' \
                    f'To suggest a venue, send a message to the main chatroom with the hashtag #barnight. ' \
                    f'You can also use @{app.BOT_USERNAME} in your message to suggest a venue.'
            await bot.send_message(message.chat.id, message_text)

        if message_lower.startswith('/delete ') or message_lower == '/delete':
            if is_admin:
                venue_name = message.text[len('/delete '):].strip()
                if not venue_name:
                    await bot.send_message(
                        message.chat.id,
                        'Usage: /delete <venue_name>'
                    )
                else:
                    suggestions = database.get_current_suggestions(bypass_cache=False)
                    suggestion = next((s for s in suggestions if s.venue == venue_name), None)
                    if suggestion:
                        try:
                            database.remove_suggestion(suggestion.uuid)
                        except:
                            await bot.send_message(
                                message.chat.id,
                                f'Was unable to remove suggestion "{venue_name}" :('
                            )
                            raise
                        await bot.send_message(
                            message.chat.id,
                            f'Successfully removed "{venue_name}" from suggestions.'
                        )
                    else:
                        await bot.send_message(
                            message.chat.id,
                            f'Could not find suggestion "{venue_name}" to remove.'
                        )
            else:
                await bot.send_message(
                    message.chat.id,
                    'Sorry, you must be an admin of the main chatroom to manage venue suggestions.'
                )

        if message_lower.startswith('/list') or message_lower == '/list':
            if database.is_user_part_of_main_chat(bot, message.from_user.id):
                suggestions = database.get_current_suggestions()
                message_text = 'Current suggested venues:\n\n'
                message_text += '\n'.join(f'{s.venue} (Suggested by @{s.user_handle})' for s in suggestions)
                await bot.send_message(message.chat.id, message_text)
            else:
                await bot.send_message(
                    message.chat.id,
                    'You must be a member of the main chatroom to list suggestions.'
                )

    elif message.chat.id == app.MAIN_CHAT_ID:
        hashtag_index = message_lower.find(app.BARNIGHT_HASHTAG)
        if hashtag_index != -1:
            left_of_hashtag = message.text[0:hashtag_index].strip()
            right_of_hashtag = message.text[hashtag_index+len(app.BARNIGHT_HASHTAG):].strip()
            if len(left_of_hashtag) > 0 and len(right_of_hashtag) > 0 \
                    or len(left_of_hashtag) == 0 and len(right_of_hashtag) == 0:
                pass
            else:
                suggestion_text = left_of_hashtag if len(left_of_hashtag) > len(right_of_hashtag) else right_of_hashtag
                await add_suggestion(suggestion_text, message.from_user.id, message.from_user.username)
