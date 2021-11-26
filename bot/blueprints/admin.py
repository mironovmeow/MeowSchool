from typing import Optional

from vkbottle.bot import Blueprint, BotLabeler, Message
from vkbottle.dispatch.rules.base import PeerRule
from bot.db import delete_user
from diary import DiaryApi

from .other import IsAdmin

labeler = BotLabeler(auto_rules=[IsAdmin, PeerRule(False)])

bp = Blueprint(name="Admin")


@bp.on.message(text="/ping")
async def admin_ping_command(message: Message):
    await message.answer("pong")


@bp.on.message(text="/delete <user_id:int>")
async def admin_delete_command(message: Message, user_id: int):
    await delete_user(user_id)
    state_peer = await bp.state_dispenser.cast(user_id)
    if state_peer:
        api: Optional[DiaryApi] = state_peer.payload.get("api")
        if api:
            await api.close()
        await bp.state_dispenser.delete(user_id)
        await bp.api.messages.send(user_id, 0, message="Ваш профиль был удалён администратором.")
    await message.answer("Выполнено!")
