"""
Private integration (all private message handler)
"""
import json
from typing import Optional, Tuple

from barsdiary.aio import APIError, DiaryApi
from loguru import logger
from vkbottle.bot import Blueprint, BotLabeler, Message, rules
from vkbottle.dispatch.dispenser import get_state_repr
from vkbottle_types.objects import MessagesTemplateActionTypeNames

from vk_bot import keyboard
from vk_bot.db import Child, User
from vk_bot.diary_infromation import diary_info, progress_average_info
from vk_bot.error_handler import diary_date_error_handler, message_error_handler

from .other import MeowState, admin_log, tomorrow

labeler = BotLabeler(auto_rules=[rules.PeerRule(False)])

bp = Blueprint(name="Private", labeler=labeler)


@bp.on.message(state=MeowState.LOGIN)
@message_error_handler.catch
async def login_handler(message: Message):
    if not message.text:  # empty
        return await start_handler(message)
    await bp.state_dispenser.set(message.peer_id, MeowState.PASSWORD, login=message.text)
    await message.answer(message="🔑 А теперь введите пароль.")


@bp.on.message(state=MeowState.PASSWORD)
@message_error_handler.catch
async def password_handler(message: Message):
    if not message.text:  # empty
        return await start_handler(message)
    login = message.state_peer.payload.get("login")
    password = message.text
    try:
        api = await DiaryApi.auth_by_login(
            "sosh.mon-ra.ru", login, password  # TODO add region select
        )
        await User.create(
            message.peer_id,
            diary_session=api.sessionid,
            diary_information=json.dumps(api.user_information),
            children=[
                Child(vk_id=message.peer_id, child_id=child_id)
                for child_id in range(len(api.user.children))
            ],
            chats=[],
        )
        await bp.state_dispenser.set(message.peer_id, MeowState.AUTH, api=api, child_id=0)

        await admin_log(f"Авторизован новый пользователь: @id{message.peer_id}")
        logger.info(f"Auth new user: id{message.peer_id}")
        await message.answer(
            message="🔓 Вы успешно авторизовались!\n"
            "Воспользуйтесь кнопками снизу или напишите /помощь (/help) для команд",
            keyboard=keyboard.MENU,
        )
    except APIError as e:
        if not e.json_success:
            await bp.state_dispenser.set(message.peer_id, MeowState.LOGIN)
            error_message = e.json.get("message")
            if error_message:
                await message.answer(
                    message=f"🚧 {error_message}\n\n🔒 Отправь первым сообщением логин."
                )
            else:
                await message.answer(
                    message="🚧 Неправильный логин или пароль. Повторите попытку ещё раз.\n\n"
                    "🔒 Отправь первым сообщением логин."
                )
            await e.session.close()
        else:  # problems with server
            raise e


@bp.on.message(state=MeowState.RE_LOGIN)
@message_error_handler.catch
async def re_auth_login_handler(message: Message):
    if not message.text:  # empty
        await bp.state_dispenser.set(message.peer_id, MeowState.RE_LOGIN)
        await message.answer(
            "🚧 Произошла непредвиденная ошибка. Это случается редко, но необходимо заново "
            "авторизоваться.\n\n🔒 Отправь первым сообщением логин.",
            dont_parse_links=True,
            keyboard=keyboard.EMPTY,
        )
    await bp.state_dispenser.set(message.peer_id, MeowState.RE_PASSWORD, login=message.text)
    await message.answer(message="🔑 А теперь введите пароль.")


@bp.on.message(state=MeowState.RE_PASSWORD)
@message_error_handler.catch
async def re_auth_password_handler(message: Message):
    if not message.text:  # empty
        await bp.state_dispenser.set(message.peer_id, MeowState.RE_LOGIN)
        await message.answer(
            "🚧 Произошла непредвиденная ошибка. Это случается редко, но необходимо заново "
            "авторизоваться.\n\n🔒 Отправь первым сообщением логин.",
            dont_parse_links=True,
            keyboard=keyboard.EMPTY,
        )
    login = message.state_peer.payload.get("login")
    password = message.text
    try:
        api = await DiaryApi.auth_by_login(
            "sosh.mon-ra.ru", login, password
        )  # TODO add region select
        user = await User.get(message.peer_id)
        user.diary_session = api.sessionid
        user.diary_information = json.dumps(api.user_information)
        await Child.update_count(message.peer_id, len(api.user.children))
        await user.save()

        for chat in user.chats:
            await bp.state_dispenser.set(
                chat.peer_id, MeowState.AUTH, api=api, user_id=user.vk_id, child_id=0
            )
            logger.debug(f"Auth chat{chat.peer_id - 2_000_000_000} complete")

        await bp.state_dispenser.set(message.peer_id, MeowState.AUTH, api=api, child_id=0)

        logger.info(f"Re-auth complete: id{message.peer_id}")
        await message.answer(
            message="🔓 Вы успешно авторизовались!\n"
            "Воспользуйтесь кнопками снизу или напишите /помощь (/help) для команд",
            keyboard=keyboard.MENU,
        )
    except APIError as e:
        if not e.json_success:
            await bp.state_dispenser.set(message.peer_id, MeowState.RE_LOGIN)
            error_message = e.json.get("message")
            if error_message:
                await message.answer(
                    message=f"🚧 {error_message}\n\n🔒 Отправь первым сообщением логин."
                )
            else:
                await message.answer(
                    message="🚧 Неправильный логин или пароль. Повторите попытку ещё раз.\n\n"
                    "🔒 Отправь первым сообщением логин."
                )
            await e.session.close()
        else:  # problems with server
            raise e


@bp.on.message(state=MeowState.NOT_AUTH)
@message_error_handler.catch
async def not_auth_handler(message: Message):
    await message.answer(message="🚧 Тех. работы. Ожидайте")
    await admin_log(f"@id{message.peer_id} не авторизован")


@bp.on.message(
    rules.PayloadRule({"command": "start"})
    | rules.CommandRule("начать")
    | rules.CommandRule("start")
)
@message_error_handler.catch
async def start_handler(message: Message):
    # if user is registered
    if message.state_peer is not None and message.state_peer.state == get_state_repr(
        MeowState.AUTH
    ):
        await message.answer(
            message="🚧 Вы уже авторизованы. Открываю меню", keyboard=keyboard.MENU
        )
    else:
        user: Optional[User] = await User.get(message.peer_id)

        # if user is not registered
        if user is None:
            # check client_info
            if MessagesTemplateActionTypeNames.CALLBACK not in message.client_info.button_actions:
                await message.answer(
                    "🚧 Вы используете приложение, в котором недоступны callback-кнопки.\n"
                    "Пользуйтесь официальными приложениями ВКонтакте на Android и iOS, "
                    "a так же сайтом vk.com.\n\n"
                    "Если вы уверены, что это ошибка, сообщите, поможем: vk.me/meow_py",
                    dont_parse_links=True,
                )
            elif message.client_info.keyboard is False:
                await message.answer(
                    "🚧 Вы используете приложение, в котором недоступны клавиатуры ботов.\n"
                    "Пользуйтесь официальными приложениями ВКонтакте на Android и iOS, "
                    "a так же сайтом vk.com.\n\n"
                    "Если вы уверены, что это ошибка, сообщите, поможем: vk.me/meow_py",
                    dont_parse_links=True,
                )
            elif message.client_info.inline_keyboard is False:
                await message.answer(
                    "🚧 Вы используете приложение, в котором недоступны "
                    "клавиатуры ботов внутри сообщений.\n"
                    "Пользуйтесь официальными приложениями ВКонтакте на Android и iOS, "
                    "a так же сайтом vk.com.\n\n"
                    "Если вы уверены, что это ошибка, сообщите, поможем: vk.me/meow_py",
                    dont_parse_links=True,
                )
            else:
                await bp.state_dispenser.set(message.peer_id, MeowState.LOGIN)
                await message.answer(
                    "👋 Добро пожаловать!\n"
                    "Здесь можно узнать домашнее задание и оценки из sosh.mon-ra.ru "
                    "Для начало работы мне нужен логин и пароль от вышеуказанного сайта.\n\n"
                    "🔒 Отправь первым сообщением логин.\n\n"
                    "🚧 Продолжая пользоваться ботом, вы соглашаетесь с нашим "
                    "пользовательским соглашением (vk.com/@schoolbot04-terms). "
                    "Обычное дело, без него мы не имеем права обрабатывать ваши данные.",
                    dont_parse_links=True,
                    keyboard=keyboard.EMPTY,
                )

        else:
            pass  # impossible


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


@bp.on.message(rules.CommandRule("меню") | rules.CommandRule("menu"), state=MeowState.AUTH)
@message_error_handler.catch
async def menu_command(message: Message):
    await message.answer("📗 Открываю меню", keyboard=keyboard.MENU)


@bp.on.message(
    rules.CommandRule("дневник", args_count=1) | rules.CommandRule("diary", args_count=1),
    state=MeowState.AUTH,
)
@diary_date_error_handler.catch
async def diary_command(message: Message, args: Tuple[str]):
    date = args[0]  # TODO add check
    api: DiaryApi = message.state_peer.payload["api"]
    child_id: int = message.state_peer.payload["child_id"]
    diary = await api.diary(date, child=child_id)
    await message.answer(
        message=diary_info(diary), keyboard=keyboard.diary_week(date), dont_parse_links=True
    )


@bp.on.message(rules.CommandRule("дневник") | rules.CommandRule("diary"), state=MeowState.AUTH)
@diary_date_error_handler.catch
async def diary_empty_command(message: Message):
    return await diary_command(message, (tomorrow(),))  # type: ignore


@bp.on.message(
    rules.CommandRule(("оценки", 1)) | rules.CommandRule(("marks", 1)), state=MeowState.AUTH
)
@diary_date_error_handler.catch
async def marks_command(message: Message, args: Tuple[str]):
    date = args[0]  # todo check
    api: DiaryApi = message.state_peer.payload["api"]
    child_id: int = message.state_peer.payload["child_id"]
    marks = await api.progress_average(date, child=child_id)
    await message.answer(
        message=progress_average_info(marks),
        keyboard=keyboard.marks_stats(date),
        dont_parse_links=True,
    )


@bp.on.message(rules.CommandRule("оценки") | rules.CommandRule("marks"), state=MeowState.AUTH)
@diary_date_error_handler.catch
async def marks_empty_command(message: Message):
    return await marks_command(message, (tomorrow(),))  # type: ignore


@bp.on.message(
    rules.CommandRule("настройки") | rules.CommandRule("settings"), state=MeowState.AUTH
)
@message_error_handler.catch
async def settings_command(message: Message):
    user = await User.get(message.peer_id)
    await message.answer(message="⚙ Настройки", keyboard=keyboard.settings(user))


# promo command
@bp.on.message(
    rules.CommandRule("вряд_ли_кто_то_будет_читать_исходники_и_найдёт_пасхалку"),
    state=MeowState.AUTH,
)
@message_error_handler.catch
async def easter_egg_command(message: Message):
    await message.answer(
        "🎉 Молодец!\nРаньше выдавался специальный бонусный донат. Теперь я не могу его дать :с"
    )


@bp.on.message(text="/<command>", state=MeowState.AUTH)
async def undefined_command(message: Message, command: str):
    await message.answer(
        message=f'🚧 Команда "/{command}" не найдена. '
        "Возможно, был использован неправильный формат.\n"
        "Воспользуйтесь командой /помощь (/help) для получения списка команд."
    )


@bp.on.message(state=MeowState.AUTH, payload_map={"menu": str})
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
            dont_parse_links=True,
        )


@bp.on.message()  # empty handler
async def empty_handler(message: Message):
    return await start_handler(message)
