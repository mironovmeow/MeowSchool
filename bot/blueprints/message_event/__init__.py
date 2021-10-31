from typing import List

from vkbottle.framework.abc_blueprint import ABCBlueprint

from . import private

message_event_bp_list: List[ABCBlueprint] = [
    private.bp,
]
