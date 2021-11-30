"""
Additional functions with blueprint integration (bp.state_dispenser and bp.api)
"""
import datetime
from typing import Tuple

from vkbottle import BaseStateGroup
from vkbottle.bot import Blueprint
from vkbottle.dispatch.dispenser import get_state_repr
from vkbottle.modules import logger

from bot import db
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


async def auth_users_and_chats() -> Tuple[int, int]:  # todo рассмотреть вариант с auth-middleware
    logger.debug("Start auth users from db")
    count_user = 0
    for peer_id, diary_session, login, password in await db.get_users():
        try:
            if diary_session:
                api = await DiaryApi.auth_by_diary_session(diary_session)
            else:
                api = await DiaryApi.auth_by_login(login, password)
            await bp.state_dispenser.set(peer_id, AuthState.AUTH, api=api)
            logger.debug(f"Auth @id{peer_id} complete")
            count_user += 1
        except APIError as e:
            logger.warning(f"Auth @id{peer_id} failed! {e}")
            await e.session.close()

    count_chat = 0
    for chat_id, user_id in await db.get_chats():
        user_state_peer = await bp.state_dispenser.get(user_id)

        # check auth of user
        if user_state_peer is None or user_state_peer.state != get_state_repr(AuthState.AUTH):
            logger.warning(f"Auth {chat_id} failed! Not found user @id{user_id}")
        else:
            await bp.state_dispenser.set(
                chat_id,
                AuthState.AUTH,
                api=user_state_peer.payload["api"],
                user_id=user_id
            )
            logger.debug(f"Auth {chat_id} complete")
            count_chat += 1

    await admin_log("Бот запущен.\n"
                    f"🔸 Авторизованных пользователей: {count_user}\n"
                    f"🔸 Авторизованных бесед: {count_chat}")
    logger.info(f"Auth of {count_user} users and {count_chat} chats complete")
    return count_user, count_chat
