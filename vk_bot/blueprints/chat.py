"""
Chat integration (all chat message handler)
"""
from typing import Tuple

from barsdiary.aio import DiaryApi
from loguru import logger
from vkbottle.bot import Blueprint, BotLabeler, Message, rules
from vkbottle.dispatch.dispenser import get_state_repr
from vkbottle_types.objects import MessagesMessageActionStatus

from vk_bot import keyboard
from vk_bot.db import Chat
from vk_bot.diary_infromation import diary_info
from vk_bot.error_handler import diary_date_error_handler, message_error_handler

from .other import MeowState, admin_log, tomorrow

labeler = BotLabeler(auto_rules=[rules.PeerRule(True)])

bp = Blueprint(name="Chat", labeler=labeler)


@bp.on.message(rules.ChatActionRule(MessagesMessageActionStatus.CHAT_INVITE_USER.value))
@message_error_handler.catch
async def invite_handler(message: Message):
    if message.action.member_id == -message.group_id:
        if message.state_peer:  # if auth  todo is it possible?
            chat = await Chat.get(message.peer_id)
            user_state_peer = await bp.state_dispenser.get(chat.vk_id)
            await bp.state_dispenser.set(
                message.peer_id,
                MeowState.AUTH,
                api=user_state_peer.payload["api"],
                user_id=message.from_id,
                child_id=0,
            )

            await message.answer(
                "🔓 Эта беседа уже авторизована! "
                "Напишите /помощь (/help) для получения списка всех команд.",
                reply_to=message.id,
            )
        else:
            await message.answer(
                "👋 Спасибо, что вы решили воспользоваться моим ботом. "
                "🔒 Напишите /начать (/start), что бы авторизовать беседу"
            )
        logger.info(f"Get new chat: {message.peer_id}")


# TODO TODO TODO TODO
@bp.on.message(state=MeowState.NOT_AUTH)
@message_error_handler.catch
async def not_auth_handler(message: Message):
    await message.answer(message="🚧 Тех. работы. Ожидайте")
    await admin_log(f"chat{message.chat_id} не авторизован")


@bp.on.message(rules.CommandRule("стоп") | rules.CommandRule("stop"))
@message_error_handler.catch
async def stop_command(message: Message):
    if not message.state_peer:  # if not auth
        await message.answer("🔒 Эта беседа не авторизована. Бота можно просто удалить из беседы")
    else:  # if auth
        user_id: int = message.state_peer.payload["user_id"]
        if message.from_id != user_id:
            await message.answer("🚧 Эту команду может вызвать только тот, кто авторизовал беседу")
        else:
            await message.answer(
                "👋 Был рад с вами поработать\n🔒 Теперь бота можно удалить из беседы"
            )
            chat = await Chat.get(message.peer_id)
            await bp.state_dispenser.delete(message.peer_id)

            if chat:
                await chat.delete()

            await admin_log(f"Бот покинул беседу.\nchat{message.chat_id}")
            logger.info(f"Leave chat: chat{message.chat_id}")


@bp.on.message(rules.CommandRule("помощь") | rules.CommandRule("help"))
@message_error_handler.catch
async def help_command(message: Message):
    await message.answer(
        "📒 Список всех команд:\n\n"
        "🔸 /помощь -- Собственно, этот список\n"
        "🔸 /начать -- Авторизовать беседу\n"
        "🔸 /стоп -- Убрать бота из беседы\n\n"
        "🔸 /дневник -- Посмотреть дневник на завтра\n"
        "🔸 /дневник дд.мм.гггг -- Посмотреть дневник на конкретное число\n\n"
        "📒 Для всех команд есть английские алиасы (help, start, stop, diary)."
    )


@bp.on.message(rules.CommandRule("начать") | rules.CommandRule("start"))
@message_error_handler.catch
async def start_command(message: Message):
    if message.state_peer is None:  # if chat is not auth
        user_state_peer = await bp.state_dispenser.get(message.from_id)

        # check auth of user
        if user_state_peer is None or user_state_peer.state != get_state_repr(MeowState.AUTH):
            await message.answer(
                "🔒 Для начала, нужно авторизоваться в личных сообщениях бота: vk.me/schoolbot04, "
                "затем здесь написать /начать (/start).",
                reply_to=message.id,
            )

        else:
            await bp.state_dispenser.set(
                message.peer_id,
                MeowState.AUTH,
                api=user_state_peer.payload["api"],
                user_id=message.from_id,
                child_id=0,
            )

            await Chat.create(message.peer_id, message.from_id)

            await message.answer(
                "🔓 Беседа авторизована успешно! "
                "Напишите /помощь (/help) для получения списка всех команд.",
                reply_to=message.id,
            )
            await admin_log(f"Новая беседа авторизована.\nchat{message.chat_id}")
            logger.info(f"Auth new chat: chat{message.chat_id}")
    else:
        await message.answer(
            "🔓 Беседа уже авторизована!\n"
            "Воспользуйтесь командой /помощь (/help) для получения списка всех команд.",
            reply_to=message.id,
        )


# todo flood control
@bp.on.message(
    rules.CommandRule(("дневник", 1)) | rules.CommandRule(("diary", 1)), state=MeowState.AUTH
)
@diary_date_error_handler.catch
async def diary_command(message: Message, args: Tuple[str]):
    date = args[0]
    api: DiaryApi = message.state_peer.payload["api"]
    child_id: int = message.state_peer.payload["child_id"]
    diary = await api.diary(date, child=child_id)
    await message.answer(
        message=diary_info(diary, is_chat=True),
        keyboard=keyboard.diary_week(date),
        dont_parse_links=True,
    )


@bp.on.message(rules.CommandRule("дневник") | rules.CommandRule("diary"), state=MeowState.AUTH)
@diary_date_error_handler.catch
async def diary_tomorrow_command(message: Message):
    return await diary_command(message, (tomorrow(),))  # type: ignore
