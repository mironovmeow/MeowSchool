"""
Additional functions with blueprint integration (bp.state_dispenser and bp.api)
"""
import datetime
import re
from asyncio import TimeoutError
from typing import Optional

from vkbottle import BaseStateGroup
from vkbottle.bot import Blueprint
from vkbottle.modules import logger

from diary import APIError, DiaryApi
from vk_bot.db import User

ADMINS = [
    248525108,  # @mironovmeow      | Миронов Данил
]


class MeowState(BaseStateGroup):
    NOT_AUTH = -3  # todo
    LOGIN = -2
    PASSWORD = -1
    AUTH = 1
    REF_CODE = 2


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


async def ref_activate(refry_user: User, referral_id: int):
    referral_count = await refry_user.referral_count()
    await bp.api.messages.send(
        refry_user.vk_id,
        message=f"🔔 Приглашён новый пользователь: @id{referral_id}",
        random_id=0
    )

    if referral_count == 3 and refry_user.donut_level < 1:
        refry_user.donut_level = 1
        await refry_user.save()
        await bp.api.messages.send(
            refry_user.vk_id,
            message="🔔 Вау, ты пригласил трёх людей в проект! Держи донатые уведомления",
            random_id=0
        )


async def get_peer_id(text: str) -> Optional[int]:
    screen_name = re.match(
        r"^(?:vk\.(?:com|me)/)?\b([a-zA-Z0-9_.]+)$",
        text
    )
    if screen_name is None:
        return None
    if screen_name.group(1).isdecimal():
        return int(screen_name.group(1))
    return (await bp.api.utils.resolve_screen_name(screen_name.group(1))).object_id


async def auth_users_and_chats():  # todo рассмотреть вариант с auth-middleware
    logger.debug("Start auth from db")
    count_user, count_chat = 0, 0
    for user in await User.get_all(chats=True, children=True):
        try:
            if user.diary_session:
                api = await DiaryApi.auth_by_diary_session(user.diary_session)
            else:
                api = await DiaryApi.auth_by_login(user.login, user.password)
            await bp.state_dispenser.set(user.vk_id, MeowState.AUTH, api=api, user=user)
            logger.debug(f"Auth id{user.vk_id} complete")
            count_user += 1

            for chat in user.chats:
                await bp.state_dispenser.set(
                    chat.chat_id,
                    MeowState.AUTH,
                    api=api,
                    user_id=user.vk_id
                )
                logger.debug(f"Auth chat{chat.chat_id - 2_000_000_000} complete")
                count_chat += 1
        except (APIError, TimeoutError):
            await bp.state_dispenser.set(user.vk_id, MeowState.NOT_AUTH, user=user)
            logger.debug(f"Auth id{user.vk_id} not complete")

            for chat in user.chats:
                await bp.state_dispenser.set(
                    chat.chat_id,
                    MeowState.NOT_AUTH,
                    user_id=user.vk_id
                )
                logger.debug(f"Auth chat{chat.chat_id - 2_000_000_000} not complete")

    await admin_log("Бот запущен.\n"
                    f"🔸 Пользователи: {count_user}\n"
                    f"🔸 Беседы: {count_chat}")
    logger.info(f"Auth of {count_user} users and {count_chat} chats complete")
