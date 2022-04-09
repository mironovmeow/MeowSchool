"""
Admin features and commands
"""
from barsdiary.aio import DiaryApi
from vkbottle.bot import Blueprint, BotLabeler, Message, rules

from vk_bot.db import Chat, Child, User
from vk_bot.error_handler import message_error_handler

from .other import ADMINS

IsAdmin = rules.FromPeerRule(ADMINS)


labeler = BotLabeler(auto_rules=[IsAdmin, rules.PeerRule(False)])

bp = Blueprint(name="Admin", labeler=labeler)


@bp.on.message(text="!ping")
@message_error_handler.catch
async def admin_ping_command(message: Message):
    await message.answer("pong")


@bp.on.message(text="!delete <vk_id:int>")
@message_error_handler.catch  # do something
async def admin_delete_command(message: Message, vk_id: int):
    state_peer = await bp.state_dispenser.get(vk_id)
    if state_peer:
        try:
            user = await User.get(vk_id)
            await user.delete()
        finally:
            pass

        try:
            api: DiaryApi = state_peer.payload["api"]
            await api.logout()
            await api.close_session()
        finally:
            pass

        await bp.state_dispenser.delete(vk_id)

        await bp.api.messages.send(vk_id, 0, message="🚧 Ваш профиль был удалён администратором.")
        await message.answer("🔸 Выполнено!")
    else:
        await message.answer("🔸 Пользователь не найден")


@bp.on.message(text="!info")
@message_error_handler.catch
async def admin_marks_command(message: Message):
    await message.answer(
        f"🔸 Пользователи: {await User.count()}\n"
        f"🔸 Беседы: {await Chat.count()}\n"
        f"🔸 Уведомления: {await Child.marks_count()}"
    )
