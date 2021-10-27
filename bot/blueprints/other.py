import datetime

from vkbottle.bot import Blueprint
from vkbottle.modules import logger
from vkbottle_types import BaseStateGroup

from bot import db
from diary import APIError, DiaryApi


class AuthState(BaseStateGroup):
    LOGIN = -2
    PASSWORD = -1
    NOT_AUTH = 0
    AUTH = 1


def today():
    return datetime.date.today().strftime("%d.%m.%Y")


ADMINS = [
    248525108,  # @mironovmeow      | Миронов Данил
]


bp = Blueprint(name="Other")  # use for .state_dispenser and .api in functions


async def admin_log(text: str):
    for peer_id in ADMINS:
        await bp.api.messages.send(
            message="Уведомление от системы!\n\n" + text,
            peer_id=peer_id,
            random_id=0
        )


async def auth_in_private_message():  # todo рассмотреть вариант с auth-middleware
    logger.debug("Start auth users from db")
    count = 0
    for peer_id, diary_session, login, password in db.get_users():
        try:
            if diary_session:
                api = await DiaryApi.auth_by_diary_session(diary_session)
            else:
                api = await DiaryApi.auth_by_login(login, password)
            await bp.state_dispenser.set(peer_id, AuthState.AUTH, api=api)
            logger.debug(f"Auth @id{peer_id} complete")
            count += 1
        except APIError as e:
            logger.warning(f"Auth @id{peer_id} failed! {e}")
            await e.session.close()

    await admin_log(f"Бот запущен. Авторизованных пользователей: {count}")
    logger.info(f"Auth of {count} users complete")
    return count
