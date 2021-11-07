from vkbottle.bot import Blueprint, Message
from vkbottle.dispatch.rules.bot import PayloadRule, PeerRule
from vkbottle.framework.bot import BotLabeler
from vkbottle.modules import logger

from bot import db, keyboards
from bot.blueprints.other import AuthState, admin_log, today
from bot.error_handler import error_handler
from diary import APIError, DiaryApi

labeler = BotLabeler()
labeler.auto_rules = [PeerRule(False)]

bp = Blueprint(name="PrivateMessage", labeler=labeler)


# startup button

@bp.on.message(PayloadRule({"command": "start"}))
@error_handler.catch
async def start_handler(message: Message):
    if "callback" not in message.client_info.button_actions:
        await message.answer(
            "Вы используете приложение, в котором недоступны callback-кнопки.\n"
            "Пользуйтесь официальными приложениями ВКонтакте на Android и iOS, a так же сайтом vk.com.",
            dont_parse_links=True
        )
        await admin_log(
            f"У [id{message.peer_id}|чувака] не поддерживаются callback. Срочно допросить!"
        )
    elif message.client_info.keyboard is False:
        await message.answer(
            "Вы используете приложение, в котором недоступны клавиатуры ботов.\n"
            "Пользуйтесь официальными приложениями ВКонтакте на Android и iOS, a так же сайтом vk.com.",
            dont_parse_links=True
        )
    elif message.client_info.inline_keyboard is False:
        await message.answer(
            "Вы используете приложение, в котором недоступны клавиатуры ботов внутри сообщений.\n"
            "Пользуйтесь официальными приложениями ВКонтакте на Android и iOS, a так же сайтом vk.com.",
            dont_parse_links=True
        )
    else:
        await bp.state_dispenser.set(message.peer_id, AuthState.LOGIN)
        await message.answer(
            "Добро пожаловать в сообщество \"Школьный бот\"!\n"
            "Здесь можно узнать домашнее задание и оценки из sosh.mon-ra.ru\n"
            "Для начало работы мне нужен логин и пароль от вышеуказанного сайта. "
            "Отправь первым сообщением логин.",
            dont_parse_links=True
        )


@bp.on.message(state=AuthState.LOGIN)
@error_handler.catch
async def password_handler(message: Message):
    await bp.state_dispenser.set(message.peer_id, AuthState.PASSWORD, login=message.text)
    await message.answer(
        message="А теперь введите пароль."
    )


@bp.on.message(state=AuthState.PASSWORD)
@error_handler.catch
async def auth_handler(message: Message):
    login = message.state_peer.payload.get("login")
    password = message.text
    try:
        api = await DiaryApi.auth_by_login(login, password)
        await bp.state_dispenser.set(message.peer_id, AuthState.AUTH, api=api)

        db.add_user(message.peer_id, login, password)

        await admin_log(f"Авторизован новый пользователь: @id{message.peer_id}")
        logger.info(f"Auth new user: @id{message.peer_id}")
        await message.answer(
            message="Добро пожаловать в главное меню.\n"
                    "Воспользуйтесь кнопками снизу",
            keyboard=keyboards.menu()
        )
    except APIError as e:  # todo message from error
        if e.json_success is False:
            await bp.state_dispenser.set(message.peer_id, AuthState.LOGIN)
            await message.answer(
                message="Неправильный логин или пароль. Повторите попытку ещё раз.\n"
                        "Отправь первым сообщением логин."
            )
        else:  # problems with server
            raise e


@bp.on.message(state=AuthState.AUTH)
@error_handler.catch
async def menu_handler(message: Message):
    api: DiaryApi = message.state_peer.payload["api"]
    menu = message.get_payload_json().get("menu")
    text, keyboard = None, None

    if menu == "diary":
        diary = await api.diary(today())
        text = diary.info()
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


# empty handlers

@bp.on.message()
@error_handler.catch
async def empty_handler(message: Message):
    if message.state_peer is not None and message.state_peer.state == AuthState.AUTH:
        await message.answer(
            message="Меню",
            keyboard=keyboards.menu()
        )
    else:
        user = db.get_user(message.peer_id)
        if user is None:
            await start_handler(message)
        else:
            login, password = user
            try:
                api = await DiaryApi.auth_by_login(login, password)
                await bp.state_dispenser.set(message.peer_id, AuthState.AUTH, api=api)
                await message.answer(
                    message="Были небольшие проблемы со сервером. Повторите операцию ещё раз."
                )
                logger.debug(f"Re-auth @id{message.peer_id} complete")
            except APIError as e:
                logger.warning(f"Re-auth @id{message.peer_id} failed! {e}")
                await e.session.close()
                await message.answer(
                    message="Временные неполадки с сайтом электронного дневника. Повторите попытку позже."
                )
