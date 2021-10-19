import datetime

from vkbottle.bot import Blueprint, Message
from vkbottle.dispatch.rules.bot import PeerRule, StateRule
from vkbottle.modules import logger
from vkbottle_types import BaseStateGroup

from bot import db, keyboards
from bot.error_handler import callback_error_handler, error_handler
from bot.rules import KeyboardRule, MessageEventKeyboardRule
from diary import APIError, DiaryApi
from vkbottle_meow import MessageEvent, MessageEventLabeler
from vkbottle_meow.rules import PeerRule as MessageEventPeerRule, StateRule as MessageEventStateRule


class AuthState(BaseStateGroup):
    LOGIN = -2
    PASSWORD = -1
    NOT_AUTH = 0
    AUTH = 1


AUTH = AuthState.AUTH


def today():
    return datetime.date.today().strftime("%d.%m.%Y")


labeler = MessageEventLabeler(custom_rules={
    "peer": PeerRule,
    "keyboard": KeyboardRule,
    "state": StateRule,
    "event_peer": MessageEventPeerRule,
    "event_keyboard": MessageEventKeyboardRule,
    "event_state": MessageEventStateRule
})


bp = Blueprint(name="PrivateMessage", labeler=labeler)


@bp.on.message(keyboard="auth", peer=False)
@error_handler.wraps_error_handler()
async def login_handler(message: Message):
    await bp.state_dispenser.set(message.peer_id, AuthState.LOGIN)
    await message.answer(
        message="Введите логин:"
    )


@bp.on.message(state=AuthState.LOGIN, peer=False)
@error_handler.wraps_error_handler()
async def password_handler(message: Message):
    await bp.state_dispenser.set(message.peer_id, AuthState.PASSWORD, login=message.text)
    await message.answer(
        message="Введите пароль:"
    )


@bp.on.message(state=AuthState.PASSWORD, peer=False)
@error_handler.wraps_error_handler()
async def auth_handler(message: Message):
    login = message.state_peer.payload.get("login")
    password = message.text
    try:
        api = await DiaryApi.auth_by_login(login, password)
        await bp.state_dispenser.set(message.peer_id, AUTH, api=api)

        db.add_user(message.peer_id, login, password)

        logger.info(f"Auth new user: @id{message.peer_id}")
        await message.answer(
            message="Добро пожаловать в главное меню.",
            keyboard=keyboards.menu()
        )
    except APIError as e:
        if e.json_success is False:
            await bp.state_dispenser.set(message.peer_id, AuthState.LOGIN)
            await message.answer(
                message="Неправильный логин или пароль. Повторите попытку\n\nВведите логин:"
            )
        else:  # problems with server
            raise e


@bp.on.message(keyboard="menu", state=AUTH, peer=False)
@error_handler.wraps_error_handler()
async def menu_handler(message: Message):
    api: DiaryApi = message.state_peer.payload["api"]
    menu = message.get_payload_json().get("menu")
    text, keyboard = None, None

    if menu == "auth":
        text = "Введите логин от электронного дневника (sosh.mon-ra.ru):"
        await bp.state_dispenser.set(message.peer_id, AuthState.LOGIN)

    elif menu == "diary":
        diary = await api.diary(today())
        text = f"РАСПИСАНИЕ УРОКОВ\n\n{diary.info()}"
        keyboard = keyboards.diary_week(today())

    elif menu == "marks":
        marks = await api.progress_average(today())
        text = marks.info()
        keyboard = keyboards.marks_stats()

    elif menu == "settings":
        text = "Сейчас здесь ничего нет, но скоро будет..."

    else:
        text = "Кнопка не найдена...\nВозврат к главному меню",
        keyboard = keyboards.menu()

    await message.answer(
        message=text,
        keyboard=keyboard,
        dont_parse_links=True
    )


@bp.on.message_event(event_keyboard="diary", event_state=AUTH, event_peer=False)
@callback_error_handler.wraps_error_handler()
async def callback_diary_handler(event: MessageEvent):
    api: DiaryApi = event.state_peer.payload["api"]
    diary = await api.diary(event.payload.get('date'))
    text = "РАСПИСАНИЕ УРОКОВ\n\n" + diary.info()
    await bp.api.messages.edit(
        peer_id=event.peer_id,
        conversation_message_id=event.conversation_message_id,
        message=text,
        keyboard=keyboards.diary_week(event.payload.get('date'))
    )


@bp.on.message_event(event_keyboard="marks", event_state=AUTH, event_peer=False)
@callback_error_handler.wraps_error_handler()
async def callback_marks_handler(event: MessageEvent):
    api: DiaryApi = event.state_peer.payload["api"]
    marks = await api.progress_average(today())
    text = marks.info(event.payload.get("more"))
    await bp.api.messages.edit(
        peer_id=event.peer_id,
        conversation_message_id=event.conversation_message_id,
        message=text,
        keyboard=keyboards.marks_stats(event.payload.get("more"))
    )


# empty handlers

@bp.on.message(peer=False)
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
            await bp.state_dispenser.set(message.peer_id, AuthState.NOT_AUTH)
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
                await bp.state_dispenser.set(message.peer_id, AUTH, api=api)
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


@bp.on.message_event(event_peer=False)
@callback_error_handler.wraps_error_handler()
async def empty_callback_handler(event: MessageEvent):
    if event.state_peer is not None and event.state_peer.state == AUTH:
        await event.show_snackbar("Странно, но кнопка не найдена...")
    else:
        await bp.state_dispenser.set(event.peer_id, AuthState.NOT_AUTH)
        await bp.api.messages.send(
            peer_id=event.peer_id,
            message="Добро пожаловать в моего бота!\n"
                    "К сожалению, я не могу найти ваш профиль здесь\n"
                    "Пройдите авторизацию",
            keyboard=keyboards.auth(),
            random_id=0
        )


async def auth_in_private_message():
    logger.debug("Start auth users from db")
    count = 0
    for peer_id, diary_session, login, password in db.get_users():
        try:
            if diary_session:
                api = await DiaryApi.auth_by_diary_session(diary_session)
            else:
                api = await DiaryApi.auth_by_login(login, password)
            await bp.state_dispenser.set(peer_id, AUTH, api=api)
            logger.debug(f"Auth @id{peer_id} complete")
            count += 1
        except APIError as e:
            logger.warning(f"Auth @id{peer_id} failed! {e}")
            await e.session.close()

    logger.info(f"Auth of {count} users complete")
    return count