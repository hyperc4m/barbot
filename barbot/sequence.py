"""
Lambda functions intended to be called from Step Functions go here
"""
import asyncio
import random
from typing import Dict, Any, List

import telegram

from . import app, database


bot = telegram.Bot(
    token=app.TELEGRAM_BOT_TOKEN
)


def handle_function_call(event: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    event_type = event['barnight_event_type']
    func = event_funcs[event_type]
    return app.asyncio_loop.run_until_complete(func(event))


async def handle_ask_for_suggestions(event: Dict[str, Any]) -> Dict[str, Any]:
    await bot.send_message(
        chat_id=app.MAIN_CHAT_ID,
        text=f'It\'s time for bar night suggestions! Message @{app.BOT_USERNAME} or end a message with '
             f'{app.BARNIGHT_HASHTAG} to input a suggestion!'
    )
    return {}


async def handle_create_poll(event: Dict[str, Any]) -> Dict[str, Any]:
    database.set_current_poll_id(0)
    suggestions = database.get_current_suggestions(bypass_cache=True)

    if len(suggestions) == 0:
        send_message_result = await bot.send_message(
            chat_id=app.MAIN_CHAT_ID,
            text='Oops! No one suggested anything for barnight. I\'m gonna sit this one out...',
        )
    elif len(suggestions) == 1:
        send_message_result = await bot.send_message(
            chat_id=app.MAIN_CHAT_ID,
            text=f'There was only one suggestion, and it was for {suggestions[0].venue}.'
        )
        await bot.pin_chat_message(chat_id=app.MAIN_CHAT_ID, message_id=send_message_result.id)
    else:
        send_poll_result = await bot.send_poll(
            chat_id=app.MAIN_CHAT_ID,
            question='Where are we going for barnight? (multiple choice)',
            options=[x.venue for x in suggestions],
            is_anonymous=False,
            type='regular',
            allows_multiple_answers=True
        )
        poll_id = send_poll_result.id
        database.set_current_poll_id(poll_id)
        await bot.pin_chat_message(chat_id=app.MAIN_CHAT_ID, message_id=poll_id)

    database.clear_suggestions()
    return {}


async def handle_poll_reminder(event: Dict[str, Any]) -> Dict[str, Any]:
    poll_id = database.get_current_poll_id()
    if not poll_id:
        return {}

    await bot.send_message(
        chat_id=app.MAIN_CHAT_ID,
        text="REMINDER: Don't forget to vote!",
        reply_to_message_id=poll_id
    )
    return {}


async def handle_choose_winner(event: Dict[str, Any]) -> Dict[str, Any]:
    poll_id = database.get_current_poll_id()

    if poll_id is None:
        return {}
        # await bot.send_message(
        #     chat_id=app.MAIN_CHAT_ID,
        #     text="...this is awkward. I seem to have forgotten where the poll is."
        #          " Please find the poll and make a decision manually."
        # )
        # return {}

    poll = await bot.stop_poll(
        chat_id=app.MAIN_CHAT_ID,
        message_id=poll_id
    )

    top_options: List[telegram.PollOption] = []
    max_votes = 0

    for option in poll.options:
        if option.voter_count == max_votes:
            top_options.append(option)
        elif option.voter_count > max_votes:
            max_votes = option.voter_count
            top_options.clear()
            top_options.append(option)

    chosen_option = random.choice(top_options)

    message = f'Calling it for {chosen_option.text}!'
    if len(top_options) > 1:
        message += f' (Chosen randomly out of the top {len(top_options)} options)'

    message_result = await bot.send_message(
        chat_id=app.MAIN_CHAT_ID,
        text=message,
        reply_to_message_id=poll_id
    )

    await bot.pin_chat_message(
        chat_id=app.MAIN_CHAT_ID,
        message_id=message_result.id,
    )

    database.set_current_poll_id(0)
    return {}


EVENT_TYPE_ASK_FOR_SUGGESTIONS = 'AskForSuggestions'
EVENT_TYPE_CREATE_POLL = 'CreatePoll'
EVENT_TYPE_POLL_REMINDER = "PollReminder"
EVENT_TYPE_CHOOSE_WINNER = "ChooseWinner"

event_funcs = {
    EVENT_TYPE_ASK_FOR_SUGGESTIONS: handle_ask_for_suggestions,
    EVENT_TYPE_CREATE_POLL: handle_create_poll,
    EVENT_TYPE_POLL_REMINDER: handle_poll_reminder,
    EVENT_TYPE_CHOOSE_WINNER: handle_choose_winner
}
