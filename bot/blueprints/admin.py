from vkbottle.bot import Blueprint, BotLabeler, Message
from vkbottle.dispatch.rules.base import PeerRule

from .other import IsAdmin

labeler = BotLabeler(auto_rules=[IsAdmin, PeerRule(False)])

bp = Blueprint(name="Admin")


@bp.on.message(command="ping")
async def ping(message: Message):
    await message.answer("pong")
