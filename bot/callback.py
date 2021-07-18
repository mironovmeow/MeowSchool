"""
My module for callback handler view
"""

from typing import List, Callable, Any, Dict, Type

from vkbottle import GroupEventType, GroupTypes
from vkbottle.bot import Bot
from vkbottle.dispatch.handlers import FromFuncHandler
from vkbottle.modules import logger

from rules import ABCCallbackRule, ABCRule


class Callback:
    def __init__(self, custom_rules: Dict[str, Type[ABCRule]], state_dispenser):
        self.state_dispenser = state_dispenser
        self.handlers: List[FromFuncHandler] = []
        self.custom_rules = custom_rules
        self.rule_config = {}

    def __call__(self, *rules: ABCCallbackRule, blocking: bool = True, **custom_rules: Any):
        def decorator(func: Callable):
            self.handlers.append(FromFuncHandler(
                func,
                *rules,
                *self.get_custom_rules(custom_rules),
                blocking=blocking
            ))
            return func
        return decorator

    def get_custom_rules(self, custom_rules: Dict[str, Any]) -> List["ABCRule"]:
        return [self.custom_rules[k].with_config(self.rule_config)(v) for k, v in custom_rules.items()]  # type: ignore

    def view(self, bot: Bot):
        async def decorate_callback_handler(event: GroupTypes.MessageEvent):
            event.object.state_peer = await self.state_dispenser.get(event.object.peer_id)
            logger.debug("Handling event ({}) with meow callback view".format(event.object.event_id))
            for handler in self.handlers:
                context_variables = {}
                result = await handler.filter(event)
                logger.debug("Handler {} returned {}".format(handler, result))
                if result is False:
                    continue
                elif isinstance(result, dict):
                    context_variables.update(result)
                handler_response = await handler.handle(event, **context_variables)

                # todo: add return manager

                if handler.blocking:
                    break
        decorate_callback_handler = bot.on.raw_event(
            GroupEventType.MESSAGE_EVENT,
            GroupTypes.MessageEvent
        )(decorate_callback_handler)
        return decorate_callback_handler
