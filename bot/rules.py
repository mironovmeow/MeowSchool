"""
My module for keyboard rules
"""
from vkbottle.bot import Message
from vkbottle.dispatch.rules.bot import ABCMessageRule

from vkbottle_meow import ABCMessageEventRule, MessageEvent


class KeyboardRule(ABCMessageRule):
    def __init__(self, keyboard: str):
        self.keyboard = keyboard

    async def check(self, message: Message) -> bool:
        payload = message.get_payload_json()
        if payload is None:
            return False
        return payload.get("keyboard") == self.keyboard


class MessageEventKeyboardRule(ABCMessageEventRule):
    def __init__(self, keyboard: str):
        self.keyboard = keyboard

    async def check(self, event: MessageEvent) -> bool:
        payload = event.payload
        if payload is None:
            return False
        return payload.get("keyboard") == self.keyboard
