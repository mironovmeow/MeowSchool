"""
My module for keyboard rules
"""
from abc import abstractmethod
from typing import Union, List

from vkbottle.bot import Message
from vkbottle.dispatch.rules.abc import ABCRule
from vkbottle.dispatch.rules.bot import ABCMessageRule
from vkbottle_types import BaseStateGroup

from bot.views import MessageEvent


class KeyboardRule(ABCMessageRule):
    def __init__(self, keyboard: str):
        self.keyboard = keyboard

    async def check(self, message: Message):
        payload = message.get_payload_json()
        if payload is None:
            return False
        return payload.get("keyboard") == self.keyboard


class ABCCallbackRule(ABCRule):
    @abstractmethod
    async def check(self, event: MessageEvent) -> bool:
        pass


class CallbackKeyboardRule(ABCCallbackRule):
    def __init__(self, keyboard: str):
        self.keyboard = keyboard

    async def check(self, event: MessageEvent) -> bool:
        payload = event.payload
        return payload.get("keyboard") == self.keyboard


class CallbackStateRule(ABCCallbackRule):
    def __init__(self, state: Union[List[BaseStateGroup], BaseStateGroup]):
        if not isinstance(state, list):
            state = [] if state is None else [state]
        self.state = state

    async def check(self, event: MessageEvent) -> bool:
        if event.state_peer is None:
            return not self.state
        return event.state_peer.state in self.state
