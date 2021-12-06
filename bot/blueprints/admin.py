"""
Admin features and commands
"""
from vkbottle.bot import Blueprint, BotLabeler, Message, rules

from bot.db import Chat, Child, User
from bot.error_handler import message_error_handler
from diary import DiaryApi
from . import scheduler
from .other import ADMINS

IsAdmin = rules.FromPeerRule(ADMINS)


labeler = BotLabeler(auto_rules=[IsAdmin, rules.PeerRule(False)])

bp = Blueprint(name="Admin")


@bp.on.message(text="/ping")
@message_error_handler.catch
async def admin_ping_command(message: Message):
    await message.answer("pong")


@bp.on.message(text="/delete <vk_id:int>")
@message_error_handler.catch
async def admin_delete_command(message: Message, vk_id: int):
    state_peer = await bp.state_dispenser.get(vk_id)
    if state_peer:
        user: User = state_peer.payload["user"]
        await user.delete()

        api: DiaryApi = state_peer.payload["api"]
        await api.close()

        await bp.state_dispenser.delete(vk_id)

        await bp.api.messages.send(vk_id, 0, message="Ваш профиль был удалён администратором.")
        await message.answer("Выполнено!")
    else:
        await message.answer("Пользователь не найден")


Marks = ["выключен", "обычный", "донат", "вип", "админ"]


@bp.on.message(text="/marks <vk_id:int> <marks:int>")
@message_error_handler.catch
async def admin_marks_command(message: Message, vk_id: int, marks: int):
    state_peer = await bp.state_dispenser.get(vk_id)
    if marks < 0 or marks > 4:
        await message.answer("Неверный уровень уведомлений оценки")
    elif not state_peer:
        await message.answer("Пользователь не найден")
    else:
        user: User = state_peer.payload["user"]
        for child in user.children:
            child.marks = marks
            if marks == 0:
                await scheduler.delete(child)
            else:
                await scheduler.add(child)
        await user.save()

        await bp.api.messages.send(
            vk_id, 0,
            message=f"Ваш уровень по уведомлениям был изменён администратором на \"{Marks[marks]}\"."
        )
        await message.answer("Выполнено!")


@bp.on.message(text="/info")
@message_error_handler.catch
async def admin_marks_command(message: Message):
    await message.answer(
        f"🔸 Пользователи: {await User.count()}\n"
        f"🔸 Беседы: {await Chat.count()}\n"
        f"🔸 Уведомления: {await Child.marks_count()}"
    )
