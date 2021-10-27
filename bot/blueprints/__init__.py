from typing import List

from vkbottle.framework.abc_blueprint import ABCBlueprint

from . import other
from .message import message_bp_list
from .message_event import message_event_bp_list

bp_list: List[ABCBlueprint] = [
    other.bp,  # for activate bp.state_dispenser and bp.api in functions
    *message_bp_list,
    *message_event_bp_list,
]
