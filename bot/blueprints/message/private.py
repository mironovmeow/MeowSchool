from typing import Tuple

from vkbottle.bot import Blueprint, Message
from vkbottle.dispatch.dispenser import get_state_repr
from vkbottle.dispatch.rules.bot import CommandRule, PayloadRule, PeerRule
from vkbottle.framework.bot import BotLabeler
from vkbottle.modules import logger
from vkbottle_types.objects import MessagesTemplateActionTypeNames

from bot import db, keyboards
from bot.blueprints.other import AuthState, admin_log, today
from bot.error_handler import diary_date_error_handler, error_handler
from diary import APIError, DiaryApi

labeler = BotLabeler(auto_rules=[PeerRule(False)])

bp = Blueprint(name="PrivateMessage", labeler=labeler)


# startup button

@bp.on.message(PayloadRule({"command": "start"}))
@error_handler.catch
async def start_handler(message: Message):
    if MessagesTemplateActionTypeNames.CALLBACK not in message.client_info.button_actions:
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


# command handlers

@bp.on.message(CommandRule("помощь") | CommandRule("help"))
@error_handler.catch
async def help_command(message: Message):
    await message.answer(
        "Список всех команд:\n\n"
        "/помощь /help -- Собственно, этот список\n"
        "/начать /start -- Начать авторизацию в боте\n"
        "\nКоманды, повторяющие меню:\n"
        "/дневник [дд.мм.гггг] /diary [dd.mm.yyyy] -- Посмотреть дневник (домашнее задания, оценки)\n"
        "/оценки [дд.мм.гггг] /marks [dd.mm.yyyy]-- Посмотреть оценки\n"
        "/настройки /settings -- Настройки бота"
    )


@bp.on.message(CommandRule("дневник", args_count=1) | CommandRule("diary", args_count=1), state=AuthState.AUTH)
@diary_date_error_handler.catch
async def diary_command(message: Message, args: Tuple[str]):
    date = args[0]
    api: DiaryApi = message.state_peer.payload["api"]
    diary = await api.diary(date)
    await message.answer(
        message=diary.info(),
        keyboard=keyboards.diary_week(date),
        dont_parse_links=True
    )


@bp.on.message(CommandRule("оценки", args_count=1) | CommandRule("marks", args_count=1), state=AuthState.AUTH)
@diary_date_error_handler.catch
async def marks_command(message: Message, args: Tuple[str]):
    date = args[0]
    api: DiaryApi = message.state_peer.payload["api"]
    marks = await api.progress_average(date)
    await message.answer(
        message=marks.info(),
        keyboard=keyboards.marks_stats(date),
        dont_parse_links=True
    )


@bp.on.message(CommandRule("настройки") | CommandRule("settings"), state=AuthState.AUTH)
@error_handler.catch
async def settings_command(message: Message):
    await message.answer(
        message="Сейчас здесь ничего нет, но скоро будет..."
    )


@bp.on.message(state=AuthState.AUTH, payload_map={"menu": str})
@error_handler.catch
async def menu_handler(message: Message):
    menu = message.get_payload_json().get("menu")

    if menu == "diary":
        await diary_command(message, (today(),))  # type: ignore

    elif menu == "marks":
        await marks_command(message, (today(),))  # type: ignore

    elif menu == "settings":
        await settings_command(message)

    else:
        await message.answer(
            message="Кнопка не найдена...\nВозврат к главному меню",
            keyboard=keyboards.menu(),
            dont_parse_links=True
        )


@bp.on.message()  # empty handlers
@bp.on.message(CommandRule("начать") | CommandRule("start"))
@error_handler.catch
async def empty_handler(message: Message):
    if message.state_peer is not None and message.state_peer.state == get_state_repr(AuthState.AUTH):
        await message.answer(
            message="Вы уже авторизованы. Открываю меню",
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
