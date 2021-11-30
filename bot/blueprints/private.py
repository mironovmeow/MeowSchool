"""
Private integration (all private message handler)
"""
from typing import Tuple

from vkbottle.bot import Blueprint, BotLabeler, Message, rules
from vkbottle.dispatch.dispenser import get_state_repr
from vkbottle.modules import logger
from vkbottle_types.objects import MessagesTemplateActionTypeNames

from bot import db, keyboard
from bot.blueprints.other import AuthState, admin_log, tomorrow
from bot.error_handler import diary_date_error_handler, message_error_handler
from diary import APIError, DiaryApi

labeler = BotLabeler(auto_rules=[rules.PeerRule(False)])

bp = Blueprint(name="PrivateMessage", labeler=labeler)


@bp.on.message(state=AuthState.LOGIN)
@message_error_handler.catch
async def login_handler(message: Message):
    if not message.text:  # empty
        return await start_handler(message)
    await bp.state_dispenser.set(message.peer_id, AuthState.PASSWORD, login=message.text)
    await message.answer(
        message="🔑 А теперь введите пароль."
    )


@bp.on.message(state=AuthState.PASSWORD)
@message_error_handler.catch
async def password_handler(message: Message):
    if not message.text:  # empty
        return await start_handler(message)
    login = message.state_peer.payload.get("login")
    password = message.text
    try:
        api = await DiaryApi.auth_by_login(login, password)
        await bp.state_dispenser.set(message.peer_id, AuthState.AUTH, api=api)

        await db.add_user(message.peer_id, login, password)

        await admin_log(f"Авторизован новый пользователь: @id{message.peer_id}")
        logger.info(f"Auth new user: @id{message.peer_id}")
        await message.answer(
            message="🔓 Вы успешно авторизовались!\n"
                    "Воспользуйтесь кнопками снизу",
            keyboard=keyboard.MENU
        )
    except APIError as e:
        if e.json_not_success:
            await bp.state_dispenser.set(message.peer_id, AuthState.LOGIN)
            error_message = e.json.get("message")
            if error_message:
                await message.answer(
                    message=f"🚧 {error_message}\n\n"
                            "🔒 Отправь первым сообщением логин."
                )
            else:
                await message.answer(
                    message="🚧 Неправильный логин или пароль. Повторите попытку ещё раз.\n\n"
                            "🔒 Отправь первым сообщением логин."
                )
            await e.session.close()
        else:  # problems with server
            raise e


@bp.on.message(rules.PayloadRule({"command": "start"}))  # startup button
@bp.on.message(rules.CommandRule("начать") | rules.CommandRule("start"))
@message_error_handler.catch
async def start_handler(message: Message):
    # if user is registered
    if message.state_peer is not None and message.state_peer.state == get_state_repr(AuthState.AUTH):
        await message.answer(
            message="🚧 Вы уже авторизованы. Открываю меню",
            keyboard=keyboard.MENU
        )
    else:
        user = await db.get_user(message.peer_id)

        # if user not registered
        if user is None:
            # check client_info
            if MessagesTemplateActionTypeNames.CALLBACK not in message.client_info.button_actions:
                await message.answer(
                    "🚧 Вы используете приложение, в котором недоступны callback-кнопки.\n"
                    "Пользуйтесь официальными приложениями ВКонтакте на Android и iOS, a так же сайтом vk.com.",
                    dont_parse_links=True
                )
                await admin_log(
                    f"У [id{message.peer_id}|чувака] не поддерживаются callback. Срочно допросить!"
                )
            elif message.client_info.keyboard is False:
                await message.answer(
                    "🚧 Вы используете приложение, в котором недоступны клавиатуры ботов.\n"
                    "Пользуйтесь официальными приложениями ВКонтакте на Android и iOS, a так же сайтом vk.com.",
                    dont_parse_links=True
                )
            elif message.client_info.inline_keyboard is False:
                await message.answer(
                    "🚧 Вы используете приложение, в котором недоступны клавиатуры ботов внутри сообщений.\n"
                    "Пользуйтесь официальными приложениями ВКонтакте на Android и iOS, a так же сайтом vk.com.",
                    dont_parse_links=True
                )
            else:
                await bp.state_dispenser.set(message.peer_id, AuthState.LOGIN)
                await message.answer(
                    "👋 Добро пожаловать!\n"
                    "Здесь можно узнать домашнее задание и оценки из sosh.mon-ra.ru "
                    "Для начало работы мне нужен логин и пароль от вышеуказанного сайта.\n\n"
                    "🔒 Отправь первым сообщением логин.",
                    dont_parse_links=True,
                    keyboard=keyboard.EMPTY
                )

        # if user in db
        else:
            login, password = user
            try:
                api = await DiaryApi.auth_by_login(login, password)
                await bp.state_dispenser.set(message.peer_id, AuthState.AUTH, api=api)
                await message.answer(
                    message="🚧 Были небольшие проблемы со сервером. Повторите операцию ещё раз."
                )
                logger.debug(f"Re-auth @id{message.peer_id} complete")
            except APIError as e:
                logger.warning(f"Re-auth @id{message.peer_id} failed! {e}")
                await e.session.close()
                await message.answer(
                    message="🚧 Временные неполадки с сайтом электронного дневника. Повторите попытку позже."
                )


# command handlers

@bp.on.message(rules.CommandRule("помощь") | rules.CommandRule("help"))
@message_error_handler.catch
async def help_command(message: Message):
    await message.answer(
        "📒 Список всех команд:\n\n"
        "🔸 /помощь -- Собственно, этот список\n"
        "🔸 /начать -- Начать авторизацию в боте\n"
        "🔸 /меню -- Открыть меню\n\n"
        "📒 Команды, повторяющие меню:\n"
        "🔸 /дневник дд.мм.гггг -- Посмотреть дневник (домашнее задания, оценки)\n"
        "🔸 /оценки дд.мм.гггг -- Посмотреть оценки\n"
        "🔸 /настройки -- Настройки бота\n\n"
        "📒 Для всех команд есть английские алиасы (help, start, menu, diary, marks, settings)."
    )


@bp.on.message(rules.CommandRule("меню") | rules.CommandRule("menu"), state=AuthState.AUTH)
@message_error_handler.catch
async def menu_command(message: Message):
    await message.answer(
        "📗 Открываю меню",
        keyboard=keyboard.MENU
    )


@bp.on.message(
    rules.CommandRule("дневник", args_count=1) | rules.CommandRule("diary", args_count=1),
    state=AuthState.AUTH
)
@diary_date_error_handler.catch
async def diary_command(message: Message, args: Tuple[str]):
    date = args[0]
    api: DiaryApi = message.state_peer.payload["api"]
    diary = await api.diary(date)
    await message.answer(
        message=diary.info(),
        keyboard=keyboard.diary_week(date, api.user.children),
        dont_parse_links=True
    )


@bp.on.message(rules.CommandRule("дневник") | rules.CommandRule("diary"), state=AuthState.AUTH)
@diary_date_error_handler.catch
async def diary_empty_command(message: Message):
    return await diary_command(message, (tomorrow(),))  # type: ignore


@bp.on.message(rules.CommandRule(("оценки", 1)) | rules.CommandRule(("marks", 1)), state=AuthState.AUTH)
@diary_date_error_handler.catch
async def marks_command(message: Message, args: Tuple[str]):
    date = args[0]
    api: DiaryApi = message.state_peer.payload["api"]
    marks = await api.progress_average(date)
    await message.answer(
        message=marks.info(),
        keyboard=keyboard.marks_stats(date, api.user.children),
        dont_parse_links=True
    )


@bp.on.message(rules.CommandRule("оценки") | rules.CommandRule("marks"), state=AuthState.AUTH)
@diary_date_error_handler.catch
async def marks_empty_command(message: Message):
    return await marks_command(message, (tomorrow(),))  # type: ignore


@bp.on.message(rules.CommandRule("настройки") | rules.CommandRule("settings"), state=AuthState.AUTH)
@message_error_handler.catch
async def settings_command(message: Message):
    await message.answer(
        message="🚧 Сейчас здесь ничего нет, но скоро будет..."
    )


@bp.on.message(text="/<command>", state=AuthState.AUTH)
async def undefined_command(message: Message, command: str):
    await message.answer(
        message=f"🚧 Команда \"/{command}\" не найдена. Возможно, был использован неправильный формат.\n"
                "Воспользуйтесь командой /помощь (/help) для получения списка команд."
    )


@bp.on.message(state=AuthState.AUTH, payload_map={"menu": str})
@message_error_handler.catch
async def menu_handler(message: Message):
    menu = message.get_payload_json().get("menu")

    if menu == "diary":
        await diary_command(message, (tomorrow(),))  # type: ignore

    elif menu == "marks":
        await marks_command(message, (tomorrow(),))  # type: ignore

    elif menu == "settings":
        await settings_command(message)

    else:
        await message.answer(
            message="🚧 Кнопка не найдена...\nВозврат в главное меню",
            keyboard=keyboard.MENU,
            dont_parse_links=True
        )


@bp.on.message()  # empty handlers
async def empty_handler(message: Message):
    return await start_handler(message)
