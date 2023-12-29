from typing import List

from barbot.database import Suggestion


def get_list_suggestions_message_text(suggestions: List[Suggestion]) -> str:
    return '\n'.join(f'{s.venue} (Suggested by @{s.user_handle})' for s in suggestions)
