"""
Error handlers (catch all errors in handlers, vkbottle)
"""
from typing import Tuple

from aiohttp import ClientError
from loguru import logger
from vkbottle import ErrorHandler, VKAPIError
from vkbottle.bot import Message, MessageEvent

from diary.types import APIError
from .blueprints.other import admin_log
from .db import Child

message_error_handler = ErrorHandler(redirect_arguments=True)


@message_error_handler.register_error_handler(APIError)
async def message_handler_diary_api(e: APIError, m: Message):
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
        await admin_log("Неверный запрос к серверу. Проверить")

    else:
        await admin_log("В error_handler.py ошибка (1)")  # Это не должно произойти


@message_error_handler.register_error_handler(VKAPIError)
async def message_handler_vk_api(e: VKAPIError, m: Message):
    logger.warning(f"VKApi error {e.description} {e.code}")
    await m.answer("🚧 Неизвестная ошибка с VK 0_o")


@message_error_handler.register_undefined_error_handler
async def message_handler(e: BaseException, m: Message):
    logger.exception(f"Undefined error {e}")
    await m.answer("🚧 Неизвестная ошибка 0_o")


callback_error_handler = ErrorHandler(redirect_arguments=True)


@callback_error_handler.register_error_handler(APIError)
async def callback_handler_diary_api(e: APIError, event: MessageEvent):
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


@callback_error_handler.register_error_handler(VKAPIError[909])
async def callback_handler_vk_api_909(e: VKAPIError, event: MessageEvent):
    logger.info(f"VKApi edit message error {e.description} {e.code}")
    await event.show_snackbar("🚧 Сообщение слишком старое. Ещё раз напишите команду или нажмите на кнопку в меню")


@callback_error_handler.register_error_handler(VKAPIError)
async def callback_handler_vk_api(e: VKAPIError, event: MessageEvent):
    logger.warning(f"VKApi error {e.description} {e.code}")
    await event.show_snackbar("🚧 Неизвестная ошибка с VK 0_o")


@callback_error_handler.register_undefined_error_handler
async def callback_handler(e: BaseException, event: MessageEvent):
    logger.exception(f"Undefined error {e}")
    await event.show_snackbar("🚧 Неизвестная ошибка 0_o")


diary_date_error_handler = ErrorHandler(redirect_arguments=True)


@diary_date_error_handler.register_error_handler(APIError)
async def diary_date_handler(e: APIError, m: Message, args: Tuple[str]):  # todo add data checking on server side
    if e.json_not_success:
        logger.debug(f"{e}: Wrong date {args[0]}")
        await m.answer("🚧 Указана неверная дата. Попробуйте ещё раз")
    else:
        await message_handler_diary_api(e, m)


@diary_date_error_handler.register_undefined_error_handler
async def diary_date_undefined(e: APIError, m: Message, _):
    return await message_error_handler.handle(e, m)


vkbottle_error_handler = ErrorHandler()


@vkbottle_error_handler.register_error_handler(ClientError)
async def vkbottle_handler_aiohttp(e: ClientError):
    logger.error(f"Aiohttp ClientError. Again. Ignoring: {e}")


@vkbottle_error_handler.register_undefined_error_handler
async def vkbottle_handler_undefined(_: BaseException):
    logger.exception("Error in vkbottle module")


scheduler_error_handler = ErrorHandler(True)


@scheduler_error_handler.register_error_handler(APIError)
async def scheduler_handler_diary_api(e: APIError, child: Child):
    logger.warning(f"Server error {e}")

# todo add more errors (for handling, of course)
