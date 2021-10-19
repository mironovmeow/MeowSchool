from typing import Any, Callable, Dict, List, Optional, Union
from warnings import warn

from loguru import logger
from vkbottle import ABCAPI, ABCHandler, ABCStateDispenser, ABCView, API, BaseMiddleware, BaseReturnManager, \
    MiddlewareResponse, convert_shorten_filter
from vkbottle.dispatch.handlers import FromFuncHandler
from vkbottle.framework.bot import BotLabeler
from vkbottle.framework.bot.labeler.default import ShortenRule
from vkbottle.modules import json
from vkbottle_types.events import MessageEvent as _MessageEvent
from vkbottle_types.events.objects.group_event_objects import MessageEventObject


class MessageEvent(MessageEventObject):
    group_id: Optional[int] = None
    unprepared_ctx_api: Optional[Any] = None

    @property
    def ctx_api(self) -> Union["ABCAPI", "API"]:
        return getattr(self, "unprepared_ctx_api")

    @property  # use for backward compatibility (event.object.user_id)
    def object(self):
        warn("Don't use \"object\" attribute for MessageEvent\n"
             "It's work without him", PendingDeprecationWarning)
        return self

    async def show_snackbar(self, text: str):
        return await self.ctx_api.messages.send_message_event_answer(
            event_id=self.event_id,
            user_id=self.user_id,
            peer_id=self.peer_id,
            event_data=json.dumps({
                "type": "show_snackbar",
                "text": text
            })
        )

    async def open_link(self, url: str):
        return await self.ctx_api.messages.send_message_event_answer(
            event_id=self.event_id,
            user_id=self.user_id,
            peer_id=self.peer_id,
            event_data=json.dumps({
                "type": "open_link",
                "link": url
            })
        )

    async def open_app(
            self,
            app_id: int,
            owner_id: Optional[int],
            app_hash: str
    ):
        return await self.ctx_api.messages.send_message_event_answer(
            event_id=self.event_id,
            user_id=self.user_id,
            peer_id=self.peer_id,
            event_data=json.dumps({
                "type": "open_app",
                "app_id": app_id,
                "owner_id": owner_id,
                "hash": app_hash
            })
        )

    async def edit_message(
            self,
            **kwargs  # todo
    ):
        kwargs["conversation_message_id"] = self.conversation_message_id
        return await self.ctx_api.messages.send(
            **kwargs
        )


class BotMessageEventReturnHandler(BaseReturnManager):
    @BaseReturnManager.instance_of(str)
    async def str_handler(self, value: str, event: MessageEvent, _: dict):
        await event.show_snackbar(value)


def message_event_min(event: dict, ctx_api: "ABCAPI") -> "MessageEvent":
    update = _MessageEvent(**event)
    message_event = MessageEvent(
        **update.object.dict(),
        group_id=update.group_id,
    )
    setattr(message_event, "unprepared_ctx_api", ctx_api)
    return message_event


class MessageEventView(ABCView):
    def __init__(self):
        self.handlers: List["ABCHandler"] = []
        self.middlewares: List["BaseMiddleware"] = []
        self.handler_return_manager = BotMessageEventReturnHandler()

    async def process_event(self, event: dict) -> bool:
        return event["type"] == "message_event"

    async def handle_event(
        self, event: dict, ctx_api: "ABCAPI", state_dispenser: "ABCStateDispenser"
    ) -> Any:

        logger.debug("Handling event ({}) with message_event view".format(event.get("event_id")))
        context_variables = {}
        message_event = message_event_min(event, ctx_api)
        message_event.state_peer = await state_dispenser.cast(message_event.peer_id)

        for middleware in self.middlewares:
            response = await middleware.pre(message_event)
            if response == MiddlewareResponse(False):
                return
            elif isinstance(response, dict):
                context_variables.update(response)

        handle_responses = []
        handlers = []

        for handler in self.handlers:
            result = await handler.filter(message_event)
            logger.debug("Handler {} returned {}".format(handler, result))

            if result is False:
                continue

            elif isinstance(result, dict):
                context_variables.update(result)

            handler_response = await handler.handle(message_event, **context_variables)
            handle_responses.append(handler_response)
            handlers.append(handler)

            return_handler = self.handler_return_manager.get_handler(handler_response)
            if return_handler is not None:
                await return_handler(
                    self.handler_return_manager, handler_response, message_event, context_variables
                )

            if handler.blocking:
                break

        for middleware in self.middlewares:
            await middleware.post(message_event, self, handle_responses, handlers)


LabeledMessageEventHandler = Callable[..., Callable[[MessageEvent], Any]]


class MessageEventLabeler(BotLabeler):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.message_event_view = MessageEventView()

    def message_event(
            self, *rules: ShortenRule, blocking: bool = True, **custom_rules
    ) -> LabeledMessageEventHandler:
        def decorator(func):
            self.message_event_view.handlers.append(
                FromFuncHandler(
                    func,
                    *map(convert_shorten_filter, rules),
                    *self.auto_rules,
                    *self.get_custom_rules(custom_rules),
                    blocking=blocking,
                )
            )
            return func
        return decorator

    def load(self, labeler: Union[BotLabeler, "MessageEventLabeler"]):
        if type(labeler) is MessageEventLabeler:
            self.message_event_view.handlers.extend(labeler.message_event_view.handlers)
            self.message_event_view.middlewares.extend(labeler.message_event_view.middlewares)
        self.message_view.handlers.extend(labeler.message_view.handlers)
        self.message_view.middlewares.extend(labeler.message_view.middlewares)
        self.raw_event_view.handlers.update(labeler.raw_event_view.handlers)
        self.raw_event_view.middlewares.extend(labeler.raw_event_view.middlewares)

    def views(self) -> Dict[str, "ABCView"]:
        return {
            "message": self.message_view,
            "message_event": self.message_event_view,
            "raw": self.raw_event_view
        }


__all__ = (
    "MessageEvent",
    "MessageEventView",
    "MessageEventLabeler"
)
