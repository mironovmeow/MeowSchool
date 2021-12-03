"""
Additional functions with blueprint integration (bp.state_dispenser and bp.api)
"""
import datetime

from vkbottle import BaseStateGroup
from vkbottle.bot import Blueprint
from vkbottle.modules import logger

from bot.db import User
from diary import APIError, DiaryApi
from .admin import ADMINS


class AuthState(BaseStateGroup):
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


async def auth_users_and_chats():  # todo рассмотреть вариант с auth-middleware
    logger.debug("Start auth users from db")
    count_user, count_chat = 0, 0
    for user in await User.get_all(chats=True, children=True):
        try:
            if user.diary_session:
                api = await DiaryApi.auth_by_diary_session(user.diary_session)
            else:
                api = await DiaryApi.auth_by_login(user.login, user.password)
            await bp.state_dispenser.set(user.vk_id, AuthState.AUTH, api=api)
            logger.debug(f"Auth @id{user.vk_id} complete")
            count_user += 1

            for chat in user.chats:
                await bp.state_dispenser.set(
                    chat.chat_id,
                    AuthState.AUTH,
                    api=api,
                    user_id=user.vk_id
                )
                logger.debug(f"Auth {chat.chat_id} complete")
                count_chat += 1
        except APIError as e:
            logger.warning(f"Auth @id{user.vk_id} failed! {e}")
            await e.session.close()

    await admin_log("Бот запущен.\n"
                    f"🔸 Авторизованных пользователей: {count_user}\n"
                    f"🔸 Авторизованных бесед: {count_chat}")
    logger.info(f"Auth of {count_user} users and {count_chat} chats complete")
