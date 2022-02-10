"""
Additional functions with blueprint integration (bp.state_dispenser and bp.api)
"""
import datetime
import json
from asyncio import TimeoutError
from typing import Optional

from vkbottle import BaseStateGroup
from vkbottle.bot import Blueprint, Message, MessageEvent
from vkbottle.modules import logger

from diary import APIError, DiaryApi
from vk_bot.db import User

ADMINS = [
    248525108,  # @mironovmeow      | Миронов Данил
]


class MeowState(BaseStateGroup):
    NOT_AUTH = -3  # todo logic
    LOGIN = -2
    PASSWORD = -1
    AUTH = 1


# todo supporting sunday
def tomorrow() -> str:
    return (datetime.date.today() + datetime.timedelta(days=1)).strftime("%d.%m.%Y")


bp = Blueprint(name="Other")


# change to admin_chat
async def admin_log(text: str):
    for peer_id in ADMINS:
        await bp.api.messages.send(
            message="🔔 Уведомление от системы!\n\n" + text,
            peer_id=peer_id,
            random_id=0
        )


async def re_auth(error: APIError, message: Optional[Message] = None, event: Optional[MessageEvent] = None):
    if message:
        logger.info(f"Re-auth {message.peer_id}")
        # todo re-auth
    elif event:
        logger.info(f"Re-auth {event.peer_id}")
        # todo re-auth
    else:
        ...


async def auth_users_and_chats():
    logger.debug("Start auth from db")
    count_user, count_chat = 0, 0
    for user in await User.get_all(chats=True, children=True):
        try:
            api = await DiaryApi.auth_by_diary_session(
                user.diary_session,
                json.loads(user.diary_information)
            )
            await bp.state_dispenser.set(user.vk_id, MeowState.AUTH, api=api, user=user, child_id=0)
            logger.debug(f"Auth id{user.vk_id} complete")
            count_user += 1

            for chat in user.chats:
                await bp.state_dispenser.set(
                    chat.peer_id,
                    MeowState.AUTH,
                    api=api,
                    user_id=user.vk_id,
                    child_id=0
                )
                logger.debug(f"Auth chat{chat.peer_id - 2_000_000_000} complete")
                count_chat += 1
        except (APIError, TimeoutError):
            await bp.state_dispenser.set(user.vk_id, MeowState.NOT_AUTH, user=user)
            logger.debug(f"Auth id{user.vk_id} not complete")

            for chat in user.chats:
                await bp.state_dispenser.set(
                    chat.peer_id,
                    MeowState.NOT_AUTH,
                    user_id=user.vk_id
                )
                logger.debug(f"Auth chat{chat.peer_id - 2_000_000_000} not complete")

    await admin_log("Бот запущен.\n"
                    f"🔸 Пользователи: {count_user}\n"
                    f"🔸 Беседы: {count_chat}")
    logger.info(f"Auth of {count_user} users and {count_chat} chats complete")
