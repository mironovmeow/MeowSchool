from typing import List

from vkbottle.framework.abc_blueprint import ABCBlueprint

from . import chat, private

message_bp_list: List[ABCBlueprint] = [
    private.bp,
    chat.bp
]
