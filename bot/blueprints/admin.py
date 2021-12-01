"""
Admin features and commands
"""
from typing import Optional

from vkbottle.bot import Blueprint, BotLabeler, Message, rules
from bot.db import session, User
from diary import DiaryApi

ADMINS = [
    248525108,  # @mironovmeow      | Миронов Данил
]
IsAdmin = rules.FromPeerRule(ADMINS)


labeler = BotLabeler(auto_rules=[IsAdmin, rules.PeerRule(False)])

bp = Blueprint(name="Admin")


@bp.on.message(text="/ping")
async def admin_ping_command(message: Message):
    await message.answer("pong")


@bp.on.message(text="/delete <user_id:int>")
async def admin_delete_command(message: Message, user_id: int):
    user: Optional[User] = await session.get(User, user_id)
    if user:
        state_peer = await bp.state_dispenser.cast(user_id)
        if state_peer:
            api: Optional[DiaryApi] = state_peer.payload.get("api")
            if api:
                await api.close()
            await bp.state_dispenser.delete(user_id)
            await bp.api.messages.send(user_id, 0, message="Ваш профиль был удалён администратором.")
        await user.delete()
        await message.answer("Выполнено!")
    else:
        await message.answer("Пользователь не найден")
