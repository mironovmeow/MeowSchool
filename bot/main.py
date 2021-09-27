import datetime
import os

from loguru import logger
from vkbottle import GroupTypes
from vkbottle.bot import Bot, Message, BotLabeler
from vkbottle.dispatch.rules.bot import StateRule
from vkbottle_types import BaseStateGroup

from bot import db, keyboards
from bot.callback import Callback
from bot.rules import KeyboardRule, CallbackKeyboardRule, CallbackStateRule
from diary import DiaryApi, APIError


class AuthState(BaseStateGroup):
    LOGIN = -2
    PASSWORD = -1
    NOT_AUTH = 0
    AUTH = 1


def today():
    return datetime.date.today().strftime("%d.%m.%Y")


AUTH = AuthState.AUTH

labeler = BotLabeler(custom_rules={
    "keyboard": KeyboardRule,
    "state": StateRule
})

bot = Bot(os.environ["VK_TOKEN"], labeler=labeler)

callback = Callback(custom_rules={
    "keyboard": CallbackKeyboardRule,
    "state": CallbackStateRule
}, state_dispenser=bot.state_dispenser)

callback_handler = callback.view(bot)


@bot.on.message(keyboard="menu", state=AUTH)
async def menu_handler(message: Message):
    api: DiaryApi = message.state_peer.payload["api"]
    menu = message.get_payload_json().get("menu")
    text, keyboard = None, None

    if menu == "auth":
        text = "Введите логин:"
        await bot.state_dispenser.set(message.peer_id, AuthState.LOGIN)

    elif menu == "diary":
        diary = await api.diary(today())
        text = f"РАСПИСАНИЕ УРОКОВ\n\n{diary.info()}"
        keyboard = keyboards.diary_week(today())

    elif menu == "marks":
        marks = await api.progress_average(today())
        text = marks.info()
        keyboard = keyboards.marks_stats()
        # Оценки можно показывать при помощи "Календаря"
        # За неделю показывать все оценки!
        #
        #

    elif menu == "settings":
        text = "Сейчас здесь ничего нет, но скоро будет..."

    else:
        text = "Кнопка не найдена...\nВозврат к главному меню",
        keyboard = keyboards.menu()

    await message.answer(
        message=text,
        keyboard=keyboard
    )


@callback(keyboard="diary", state=AUTH)
async def callback_diary_handler(event):
    api: DiaryApi = event.object.state_peer.payload["api"]
    diary = await api.diary(event.object.payload.get('date'))
    text = "РАСПИСАНИЕ УРОКОВ\n\n" + diary.info()
    await bot.api.messages.edit(
        peer_id=event.object.peer_id,
        conversation_message_id=event.object.conversation_message_id,
        message=text,
        keyboard=keyboards.diary_week(event.object.payload.get('date'))
    )


@callback(keyboard="marks", state=AUTH)
async def callback_marks_handler(event: GroupTypes.MessageEvent):
    api: DiaryApi = event.object.state_peer.payload["api"]
    marks = await api.progress_average(today())
    text = marks.info(event.object.payload.get("more"))
    await bot.api.messages.edit(
        peer_id=event.object.peer_id,
        conversation_message_id=event.object.conversation_message_id,
        message=text,
        keyboard=keyboards.marks_stats(event.object.payload.get("more"))
    )


@bot.on.message(keyboard="auth")
async def auth_handler(message: Message):
    await bot.state_dispenser.set(message.peer_id, AuthState.LOGIN)
    await message.answer(
        message="Введите логин:"
    )


@bot.on.message(state=AuthState.LOGIN)
async def login_handler(message: Message):
    await bot.state_dispenser.set(message.peer_id, AuthState.PASSWORD, login=message.text)
    await message.answer(
        message="Введите пароль:"
    )


@bot.on.message(state=AuthState.PASSWORD)
async def password_handler(message: Message):
    login = message.state_peer.payload.get("login")
    password = message.text
    try:
        api = await DiaryApi.auth_by_login(login, password)
        await bot.state_dispenser.set(message.peer_id, AUTH, api=api)

        db.add_user(message.peer_id, login, password)

        logger.info(f"Auth new user: @id{message.peer_id}")
        await message.answer(
            message="Добро пожаловать в главное меню.",
            keyboard=keyboards.menu()
        )
    except APIError as e:
        if e.json_success is False:
            await bot.state_dispenser.set(message.peer_id, AuthState.LOGIN)
            await message.answer(
                message="Неправильный логин или пароль. Повторите попытку\n\nВведите логин:"
            )
        else:
            raise e


@bot.on.message()
async def empty_handler(message: Message):
    if message.state_peer is not None and message.state_peer.state == AUTH:
        await message.answer(
            message="Меню",
            keyboard=keyboards.menu()
        )
    else:
        await bot.state_dispenser.set(message.peer_id, AuthState.NOT_AUTH)
        await message.answer(
            message="Добро пожаловать в моего бота!\n"
                    "К сожалению, я не могу найти ваш профиль\n"
                    "Пройдите повторную авторизацию",
            keyboard=keyboards.auth()
        )


@callback()
async def empty_callback_handler(event: GroupTypes.MessageEvent):
    if event.object.state_peer is not None and event.object.state_peer.state == AUTH:  # А вдруг?
        pass  # Кнопка не найдена
    else:
        await bot.state_dispenser.set(event.object.peer_id, AuthState.NOT_AUTH)
        await bot.api.messages.send(
            peer_id=event.object.peer_id,
            message="Добро пожаловать в моего бота!\n"
                    "К сожалению, я не могу найти ваш профиль здесь\n"
                    "Пройдите авторизацию",
            keyboard=keyboards.auth(),
            random_id=0
        )


async def auth_users_from_db():
    logger.debug("Start auth users from db")
    count = 0
    for peer_id, diary_session, login, password in db.get_users():
        try:
            if diary_session:
                api = await DiaryApi.auth_by_diary_session(diary_session)
            else:
                api = await DiaryApi.auth_by_login(login, password)
            await bot.state_dispenser.set(peer_id, AUTH, api=api)
            logger.debug(f"Auth @id{peer_id} complete")
            count += 1
        except BaseException as e:
            logger.warning(f"Auth @id{peer_id} failed! {e}")

    logger.info(f"Auth of {count} users complete")
    return count
