import datetime
import sys

from loguru import logger
from vkbottle import GroupTypes
from vkbottle.bot import Bot, Message, BotLabeler
from vkbottle.dispatch.rules.bot import StateRule
from vkbottle_types import BaseStateGroup

from bot import db, keyboards
from bot.callback import CallbackView
from bot.error_handler import error_handler, callback_error_handler, vk_error_handler
from bot.rules import KeyboardRule, CallbackKeyboardRule, CallbackStateRule
from diary import DiaryApi, APIError

if len(sys.argv) < 2:
    raise ValueError("Token is undefined")
TOKEN = sys.argv[1]


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

bot = Bot(TOKEN, labeler=labeler, error_handler=vk_error_handler)

callback = CallbackView(custom_rules={
    "keyboard": CallbackKeyboardRule,
    "state": CallbackStateRule
}, state_dispenser=bot.state_dispenser)

callback_handler = callback.view(bot)


@bot.on.message(keyboard="menu", state=AUTH)
@error_handler.wraps_error_handler()
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
@callback_error_handler.wraps_error_handler()
async def callback_diary_handler(event: GroupTypes.MessageEvent):
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
@callback_error_handler.wraps_error_handler()
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
@error_handler.wraps_error_handler()
async def auth_handler(message: Message):
    await bot.state_dispenser.set(message.peer_id, AuthState.LOGIN)
    await message.answer(
        message="Введите логин:"
    )


@bot.on.message(state=AuthState.LOGIN)
@error_handler.wraps_error_handler()
async def login_handler(message: Message):
    await bot.state_dispenser.set(message.peer_id, AuthState.PASSWORD, login=message.text)
    await message.answer(
        message="Введите пароль:"
    )


@bot.on.message(state=AuthState.PASSWORD)
@error_handler.wraps_error_handler()
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
@error_handler.wraps_error_handler()
async def empty_handler(message: Message):
    if message.state_peer is not None and message.state_peer.state == AUTH:
        await message.answer(
            message="Меню",
            keyboard=keyboards.menu()
        )
    else:
        user = db.get_user(message.peer_id)
        if user is None:
            await bot.state_dispenser.set(message.peer_id, AuthState.NOT_AUTH)
            await message.answer(
                message="Добро пожаловать в моего бота!\n"
                        "К сожалению, я не могу найти ваш профиль\n"
                        "Пройдите повторную авторизацию",
                keyboard=keyboards.auth()
            )
        else:
            login, password = user
            try:
                api = await DiaryApi.auth_by_login(login, password)
                await bot.state_dispenser.set(message.peer_id, AUTH, api=api)
                await message.answer(
                    message="Были небольшие проблемы со сервером. Повторите операцию ещё раз."
                )
                logger.debug(f"Re-auth @id{message.peer_id} complete")
            except APIError as e:
                logger.warning(f"Re-auth @id{message.peer_id} failed! {e}")
                await e.session.close()
                await message.answer(
                    message="Я вижу у вас уже есть профиль, но не получается войти.\n"
                            "Временные неполадки с сервером. Повторите попытку позже"
                )


@callback()
@callback_error_handler.wraps_error_handler()
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
        except APIError as e:
            logger.warning(f"Auth @id{peer_id} failed! {e}")
            await e.session.close()

    logger.info(f"Auth of {count} users complete")
    return count
