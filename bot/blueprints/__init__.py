from typing import List

from vkbottle.framework.abc_blueprint import ABCBlueprint

from . import admin, message_event, other
from .message import message_bp_list

bp_list: List[ABCBlueprint] = [
    admin.bp,
    *message_bp_list,
    message_event.bp,
    other.bp,  # for activate bp.state_dispenser and bp.api in functions
]
