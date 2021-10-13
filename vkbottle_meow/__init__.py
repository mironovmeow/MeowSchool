"""
Module for supporting Callback buttons (MessageEvent).

Add new class "MessageEvent", with ctx_api and feature functions, view and labeler to simple integration
in the code, some base rules and ABCMessageEventRule.

>>> from vkbottle import Bot
>>> from vkbottle_meow import MessageEventLabeler, MessageEvent
>>>
>>> bot = Bot("token", labeler=MessageEventLabeler())
>>>
>>>
>>> @bot.on.message_event()
>>> def test_snackbar(event: MessageEvent):
>>>     await event.show_snackbar("Hello world")
"""

from .main import MessageEvent, MessageEventLabeler, MessageEventView
from .rules import ABCMessageEventRule

# todo wait update vkbottle to move in another repo
