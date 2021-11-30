"""
Admin features and commands
"""
from vkbottle.bot import Blueprint, BotLabeler, Message, rules

ADMINS = [
    248525108,  # @mironovmeow      | Миронов Данил
]
IsAdmin = rules.FromPeerRule(ADMINS)


labeler = BotLabeler(auto_rules=[IsAdmin, rules.PeerRule(False)])

bp = Blueprint(name="Admin")


@bp.on.message(command="ping")
async def ping(message: Message):
    await message.answer("pong")
