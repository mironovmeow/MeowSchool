import traceback
from typing import Tuple

from aiohttp import ClientError
from loguru import logger
from vkbottle import ErrorHandler, VKAPIError
from vkbottle.bot import Message
from vkbottle_callback import MessageEvent

from bot.blueprints.other import admin_log
from diary.types import APIError

error_handler = ErrorHandler(redirect_arguments=True)


@error_handler.register_error_handler(APIError)
async def message_handler_diary_api(e: APIError, m: Message):
    if not e.resp.ok:
        if e.resp.status == 401:
            logger.info(f"Re-auth {m.peer_id}")
            await m.answer("Проблемы с авторизацией. Необходимо переподключиться")  # todo
        else:
            logger.warning(f"Server error {e.resp.status}")
            await m.answer("Временные неполадки с сервером. Повторите попытку позже")

    elif not e.json_success:
        logger.warning(f"Server error {e.resp.status} {await e.resp.json()}")
        await m.answer("Временные неполадки с сервером. Повторите попытку позже")

    else:
        await admin_log("В error_handler.py ошибка (1)")  # Это не должно произойти


@error_handler.register_error_handler(VKAPIError)
async def message_handler_vk_api(e: VKAPIError, m: Message):
    logger.warning(f"VKApi error {e.description} {e.code}")
    await m.answer("Временные неполадки с сервером. Повторите попытку позже")


@error_handler.register_undefined_error_handler
async def message_handler(e: BaseException, m: Message):
    logger.warning(f"Undefined error {e}")
    logger.error("\n" + traceback.format_exc())
    await m.answer("Временные неполадки с сервером. Повторите попытку позже")


callback_error_handler = ErrorHandler(redirect_arguments=True)


@callback_error_handler.register_error_handler(APIError)
async def callback_handler_diary_api(e: APIError, event: MessageEvent):
    if not e.resp.ok:
        if e.resp.status == 401:
            logger.info(f"Re-auth {event.user_id}")
            await event.show_snackbar("Проблемы с авторизацией. Необходимо переподключиться")  # todo
        logger.warning(f"Server error {e.resp.status}")
        await event.show_snackbar("Временные неполадки с сервером электронного дневника. Повторите попытку позже")

    if not e.json_success:
        logger.warning(f"Server error {e.resp.status} {await e.resp.json()}")
        await event.show_snackbar("Временные неполадки с сервером. Повторите попытку позже")
    await e.session.close()


@callback_error_handler.register_error_handler(VKAPIError[909])
async def callback_handler_vk_api(e: VKAPIError, event: MessageEvent):
    logger.info(f"VKApi edit message error {e.description} {e.code}")
    await event.show_snackbar("Сообщение слишком старое. Воспользуйтесь меню снизу")


@callback_error_handler.register_error_handler(VKAPIError)
async def callback_handler_vk_api(e: VKAPIError, event: MessageEvent):
    logger.warning(f"VKApi error {e.description} {e.code}")
    await event.show_snackbar("Неизвестная ошибка с VK 0_o")


@callback_error_handler.register_undefined_error_handler
async def callback_handler(e: BaseException, event: MessageEvent):
    logger.warning(f"Undefined error {e}")
    logger.error("\n" + traceback.format_exc())
    await event.show_snackbar("Неизвестная ошибка 0_o")


diary_date_error_handler = ErrorHandler(redirect_arguments=True)


@diary_date_error_handler.register_error_handler(APIError)
async def diary_date_handler(e: APIError, m: Message, args: Tuple[str]):
    if not e.json_success:
        logger.debug(f"Wrong date {await e.resp.json()} {args[0]}")
        await m.answer("Указана неверная дата. Попробуйте ещё раз")
    else:
        await message_handler_diary_api(e, m)


vkbottle_error_handler = ErrorHandler()


@vkbottle_error_handler.register_error_handler(ClientError)
async def vkbottle_handler_aiohttp(e: ClientError):
    logger.exception("aiohttp error. Again.")


@vkbottle_error_handler.register_undefined_error_handler
async def vkbottle_handler_aiohttp(e: BaseException):
    logger.exception("UNDEFINED ERROR IN VKBOTTLE!!!")
