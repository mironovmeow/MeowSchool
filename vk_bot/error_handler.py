"""
Error handlers (catch all errors in handlers, vkbottle)
"""
from asyncio import TimeoutError
from typing import Tuple

from aiohttp import ClientError
from loguru import logger
from pydantic import ValidationError
from vkbottle import ErrorHandler, VKAPIError
from vkbottle.bot import Message, MessageEvent

from diary.types import APIError
from .blueprints.other import admin_log
from .db import Child

message_error_handler = ErrorHandler(redirect_arguments=True)


@message_error_handler.register_error_handler(APIError)
async def message_diary(e: APIError, m: Message):
    if not e.resp.ok:
        if e.resp.status == 401:
            logger.info(f"Re-auth {m.peer_id}")
            await m.answer("🚧 Проблемы с авторизацией. Необходимо переподключиться")  # todo
        else:
            logger.warning(f"{e}: Server error")
            await m.answer("🚧 Временные неполадки с сервером электронного дневника. Повторите попытку позже")

    elif e.json_not_success:
        logger.warning(f"{e}: Server error")
        await m.answer("🚧 Временные неполадки с сервером. Повторите попытку позже")
        await admin_log("Неверный запрос к серверу. Проверить!")

    else:
        await admin_log("В error_handler.py ошибка (1)")  # Это не должно произойти


@message_error_handler.register_error_handler(VKAPIError[9])
async def message_vk_9(e: VKAPIError, m: Message):
    logger.info(f"VKApi flood error: {e.description} {e.code}")
    try:
        await m.answer("🚧 Мне кажется, или начался флуд?")
    except VKAPIError[9]:  # todo?
        ...


@message_error_handler.register_error_handler(VKAPIError)
async def message_vk(e: VKAPIError, m: Message):
    logger.warning(f"VKApi error: {e.description} {e.code}")
    await m.answer("🚧 Неизвестная ошибка с VK 0_o")


@message_error_handler.register_error_handler(ValidationError)
async def message_pydantic(e: ValidationError, m: Message):  # diary.types
    logger.error(f"Pydantic error\n{e}")
    await m.answer("🚧 Ошибка сервера. Уже известно, чиним")
    await admin_log(f"Ошибка в типах у {e.model.__name__}")


@message_error_handler.register_error_handler(TimeoutError)
async def message_aiohttp_timeout(e: TimeoutError, m: Message):
    logger.info(f"Timeout error {e}")
    await m.answer("🚧 Сервер дневника не работает. Повторите попытку позже")


@message_error_handler.register_undefined_error_handler
async def message(e: BaseException, m: Message):
    logger.exception(f"Undefined error {e}")
    await m.answer("🚧 Неизвестная ошибка 0_o")


callback_error_handler = ErrorHandler(redirect_arguments=True)


@callback_error_handler.register_error_handler(APIError)
async def callback_diary(e: APIError, event: MessageEvent):
    if not e.resp.ok:
        if e.resp.status == 401:
            logger.info(f"Re-auth {event.peer_id}")
            await event.show_snackbar("🚧 Проблемы с авторизацией. Необходимо переподключиться")  # todo
        else:
            logger.warning(f"Server error {e}")
            await event.show_snackbar("🚧 Временные неполадки с сервером электронного дневника. Повторите попытку позже")

    elif e.json_not_success:
        logger.warning(f"Server error {e}")
        await event.show_snackbar("🚧 Временные неполадки с сервером. Повторите попытку позже")

    else:
        await admin_log("В error_handler.py ошибка (2)")  # Это не должно произойти


@callback_error_handler.register_error_handler(VKAPIError[9])
async def callback_vk_9(e: VKAPIError, event: MessageEvent):
    logger.info(f"VKApi flood error: {e.description} {e.code}")
    try:
        await event.show_snackbar("🚧 Мне кажется, или начался флуд?")
    except VKAPIError[9]:  # todo?
        ...


@callback_error_handler.register_error_handler(VKAPIError[909])
async def callback_vk_909(e: VKAPIError, event: MessageEvent):
    logger.info(f"VKApi edit message error: {e.description} {e.code}")
    await event.show_snackbar("🚧 Сообщение слишком старое. Ещё раз напишите команду или нажмите на кнопку в меню")


@callback_error_handler.register_error_handler(VKAPIError)
async def callback_vk(e: VKAPIError, event: MessageEvent):
    logger.warning(f"VKApi error {e.description} {e.code}")
    await event.show_snackbar("🚧 Неизвестная ошибка с VK 0_o")


@callback_error_handler.register_error_handler(ValidationError)
async def callback_pydantic(e: ValidationError, event: MessageEvent):  # diary.types
    logger.error(f"Pydantic error\n{e}")
    await event.show_snackbar("🚧 Ошибка сервера. Уже известно, чиним")
    await admin_log(f"Ошибка в типах у {e.model.__name__}")


@callback_error_handler.register_error_handler(TimeoutError)
async def callback_aiohttp_timeout(e: TimeoutError, event: MessageEvent):
    logger.info(f"Timeout error {e}")
    await event.show_snackbar("🚧 Сервер дневника не работает. Повторите попытку позже")


@callback_error_handler.register_undefined_error_handler
async def callback(e: BaseException, event: MessageEvent):
    logger.exception(f"Undefined error {e}")
    await event.show_snackbar("🚧 Неизвестная ошибка 0_o")


diary_date_error_handler = ErrorHandler(redirect_arguments=True)


# todo add data checking on server side
@diary_date_error_handler.register_error_handler(APIError)
async def diary_date_diary(e: APIError, m: Message, args: Tuple[str]):
    if e.json_not_success:
        logger.info(f"{e}: Wrong date {args[0]}")
        await m.answer("🚧 Указана неверная дата. Попробуйте ещё раз")
    else:
        await message_diary(e, m)


@diary_date_error_handler.register_undefined_error_handler
async def diary_date(e: APIError, m: Message, args):
    return await message_error_handler.handle(e, m)


vkbottle_error_handler = ErrorHandler()


@vkbottle_error_handler.register_error_handler(ClientError)
async def vkbottle_aiohttp(e: ClientError):
    logger.warning(f"Aiohttp ClientError. Ignoring\n{e}")


@vkbottle_error_handler.register_error_handler(ValidationError)
async def vkbottle_pydantic(e: ValidationError):  # vkbottle_types
    logger.error(f"Pydantic error\n{e}")
    await admin_log(f"Ошибка в типах у {e.model.__name__}")


@vkbottle_error_handler.register_undefined_error_handler
async def vkbottle(_: BaseException):
    logger.exception("Error in vkbottle module")


scheduler_error_handler = ErrorHandler(True)


@scheduler_error_handler.register_error_handler(APIError)
async def scheduler_diary(e: APIError, child: Child):
    logger.warning(f"Server error {e}")
    await admin_log(f"Ошибка в scheduler(1) у @id{child.vk_id}")


@scheduler_error_handler.register_error_handler(TimeoutError)
async def scheduler_aiohttp_timeout(e: TimeoutError, child: Child):
    logger.info(f"Timeout error {e}")


@scheduler_error_handler.register_undefined_error_handler
async def scheduler(e: BaseException, child: Child):
    logger.exception(f"Undefined error {e}")
    await admin_log(f"Ошибка в scheduler(undefined) у @id{child.vk_id}")

# todo add more errors (for handling, of course)
