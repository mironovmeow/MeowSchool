import inspect
from abc import abstractmethod
from typing import Awaitable, Callable, Coroutine, List, Union

from vkbottle import ABCRule
from vkbottle_types import BaseStateGroup

from vkbottle_meow import MessageEvent


class ABCMessageEventRule(ABCRule):
    @abstractmethod
    async def check(self, event: MessageEvent) -> bool:
        pass


class PeerRule(ABCMessageEventRule):
    def __init__(self, from_chat: bool = True):
        self.from_chat = from_chat

    async def check(self, event: MessageEvent) -> bool:
        return self.from_chat is (event.peer_id != event.user_id)


class FromPeerRule(ABCMessageEventRule):
    def __init__(self, peer_ids: Union[List[int], int]):
        if isinstance(peer_ids, int):
            peer_ids = [peer_ids]
        self.peer_ids = peer_ids

    async def check(self, event: MessageEvent) -> bool:
        return event.peer_id in self.peer_ids


class PayloadRule(ABCMessageEventRule):
    def __init__(self, payload: Union[dict, List[dict]]):
        if isinstance(payload, dict):
            payload = [payload]
        self.payload = payload

    async def check(self, event: MessageEvent) -> bool:
        return event.get_payload_json() in self.payload


class PayloadContainsRule(ABCMessageEventRule):
    def __init__(self, payload_particular_part: dict):
        self.payload_particular_part = payload_particular_part

    async def check(self, event: MessageEvent) -> bool:
        payload = event.get_payload_json(unpack_failure=lambda p: {})
        for k, v in self.payload_particular_part.items():
            if payload.get(k) != v:
                return False
        return True


# class PayloadMapRule(ABCMessageEventRule):
#     ...


class FuncRule(ABCMessageEventRule):
    def __init__(self, func: Union[Callable[[MessageEvent], Union[bool, Awaitable]]]):
        self.func = func

    async def check(self, event: MessageEvent) -> Union[dict, bool]:
        if inspect.iscoroutinefunction(self.func):
            return await self.func(event)  # type: ignore
        return self.func(event)  # type: ignore


class CoroutineRule(ABCMessageEventRule):
    def __init__(self, coroutine: Coroutine):
        self.coroutine = coroutine

    async def check(self, message: MessageEvent) -> Union[dict, bool]:
        return await self.coroutine


class StateRule(ABCMessageEventRule):
    def __init__(self, state: Union[List[BaseStateGroup], BaseStateGroup]):
        if not isinstance(state, list):
            state = [] if state is None else [state]
        self.state = state

    async def check(self, event: MessageEvent) -> bool:
        if event.state_peer is None:
            return not self.state
        return event.state_peer.state in self.state


__all__ = (
    "ABCMessageEventRule",
    "PeerRule",
    "FromPeerRule",
    "PayloadRule",
    "PayloadContainsRule",
    # "PayloadMapRule",
    "FuncRule",
    "CoroutineRule",
    "StateRule"
)
