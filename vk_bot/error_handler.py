"""
Error handlers (catch all errors in handlers, vkbottle)
"""
from asyncio import TimeoutError
from typing import Tuple, Union

from aiohttp import ClientError
from barsdiary.aio import APIError
from loguru import logger
from pydantic import ValidationError
from vkbottle import ErrorHandler, VKAPIError
from vkbottle.bot import Message, MessageEvent

from .blueprints.other import admin_log, re_auth
from .db import Child

message_error_handler = ErrorHandler(redirect_arguments=True)


@message_error_handler.register_error_handler(APIError)
async def message_diary(e: APIError, m: Message):
    if e.code == 401:
        await re_auth(e, m.peer_id)

    elif e.code >= 400:
        logger.warning(f"{e}: Server error")
        await m.answer(
            "🚧 Временные неполадки с сервером электронного дневника. Повторите попытку позже"
        )

    else:
        logger.warning(f"{e}: Server error")
        await m.answer("🚧 Временные неполадки. Повторите попытку позже")
        await admin_log("Неверный запрос к серверу. Проверить!")


@message_error_handler.register_error_handler(VKAPIError[9])
async def message_vk_9(e: VKAPIError, m: Message):
    logger.info(f"VKApi flood error: {e.description} {e.code}")
    try:
        await m.answer("🚧 Мне кажется, или начался флуд?")
    except VKAPIError[9]:  # todo?
        ...
    except BaseException as another_e:
        await message_error_handler.handle(another_e, m)


@message_error_handler.register_error_handler(VKAPIError)
async def message_vk(e: VKAPIError, m: Message):
    logger.warning(f"VKApi error: {e.description} {e.code}")
    await m.answer("🚧 Неизвестная ошибка с VK 0_o")
    await admin_log(f"Ошибка в vk. {e.code}, {m.peer_id}")


@message_error_handler.register_error_handler(ValidationError)
async def message_pydantic(e: ValidationError, m: Message):  # diary.types
    logger.error(f"Pydantic error\n{e}")
    await m.answer("🚧 Ошибка сервера. Уже известно, чиним")
    await admin_log(f"Ошибка в типах у {e.model.__name__}")


@message_error_handler.register_error_handler(TimeoutError, ClientError)
async def message_aiohttp(e: Union[TimeoutError, ClientError], m: Message):
    logger.info(f"Server error {e}")
    await m.answer("🚧 Сервер дневника не работает. Повторите попытку позже")


@message_error_handler.register_undefined_error_handler
async def message(e: BaseException, m: Message):
    logger.exception(f"Undefined error {e}")
    await m.answer("🚧 Неизвестная ошибка 0_o")
    await admin_log(f"Ошибка в message у @id{m.peer_id}")


callback_error_handler = ErrorHandler(redirect_arguments=True)


@callback_error_handler.register_error_handler(APIError)
async def callback_diary(e: APIError, event: MessageEvent):
    if e.code == 401:
        await re_auth(e, event.peer_id)

    elif e.code >= 400:
        logger.warning(f"{e}: Server error")
        await event.show_snackbar(
            "🚧 Временные неполадки с сервером электронного дневника. Повторите попытку позже"
        )

    else:
        logger.warning(f"{e}: Server error")
        await event.show_snackbar("🚧 Временные неполадки. Повторите попытку позже")
        await admin_log("Неверный запрос к серверу. Проверить!")


@callback_error_handler.register_error_handler(VKAPIError[9])
async def callback_vk_9(e: VKAPIError, event: MessageEvent):
    logger.info(f"VKApi flood error: {e.description} {e.code}")
    try:
        await event.show_snackbar("🚧 Мне кажется, или начался флуд?")
    except VKAPIError[9]:  # todo?
        ...
    except BaseException as another_e:
        await callback_error_handler.handle(another_e, event)


@callback_error_handler.register_error_handler(VKAPIError[909])
async def callback_vk_909(e: VKAPIError, event: MessageEvent):
    logger.info(f"VKApi edit message error: {e.description} {e.code}")
    await event.show_snackbar(
        "🚧 Сообщение слишком старое. Ещё раз напишите команду или нажмите на кнопку в меню"
    )


@callback_error_handler.register_error_handler(VKAPIError)
async def callback_vk(e: VKAPIError, event: MessageEvent):
    logger.warning(f"VKApi error {e.description} {e.code}")
    await event.show_snackbar("🚧 Неизвестная ошибка с VK 0_o")
    await admin_log(f"Ошибка в vk. {e.code}, {event.peer_id}")


@callback_error_handler.register_error_handler(ValidationError)
async def callback_pydantic(e: ValidationError, event: MessageEvent):  # diary.types
    logger.error(f"Pydantic error\n{e}")
    await event.show_snackbar("🚧 Ошибка сервера. Уже известно, чиним")
    await admin_log(f"Ошибка в типах у {e.model.__name__}")


@callback_error_handler.register_error_handler(TimeoutError, ClientError)
async def callback_aiohttp(e: Union[TimeoutError, ClientError], event: MessageEvent):
    logger.info(f"Server error {e}")
    await event.show_snackbar("🚧 Сервер дневника не работает. Повторите попытку позже")


@callback_error_handler.register_undefined_error_handler
async def callback(e: BaseException, event: MessageEvent):
    logger.exception(f"Undefined error {e}")
    await event.show_snackbar("🚧 Неизвестная ошибка 0_o")
    await admin_log(f"Ошибка в callback у @id{event.peer_id}")


diary_date_error_handler = ErrorHandler(redirect_arguments=True)


@diary_date_error_handler.register_error_handler(APIError)
async def diary_date_diary(e: APIError, m: Message, args: Tuple[str]):
    if e.code == 401:
        await re_auth(e, m.peer_id)
    elif not e.json_success:
        logger.info(f"{e}: Wrong date {args[0]}")
        await m.answer("🚧 Указана неверная дата. Попробуйте ещё раз")
    else:
        await message_diary(e, m)


@diary_date_error_handler.register_undefined_error_handler
async def diary_date(e: BaseException, m: Message, _):
    return await message_error_handler.handle(e, m)


vkbottle_error_handler = ErrorHandler()


@vkbottle_error_handler.register_error_handler(ClientError)
async def vkbottle_aiohttp(e: ClientError):
    logger.info(f"Ignoring {e}")
    await admin_log(f"Ошибка в aiohttp vkbottle\n{e}")


@vkbottle_error_handler.register_error_handler(ValidationError)
async def vkbottle_pydantic(e: ValidationError):  # vkbottle_types
    logger.error(f"Pydantic error\n{e}")
    await admin_log(f"Ошибка в типах у {e.model.__name__}")


@vkbottle_error_handler.register_undefined_error_handler
async def vkbottle(_: BaseException):
    logger.exception("Error in vkbottle module")
    await admin_log("Ошибка в vkbottle")


scheduler_error_handler = ErrorHandler(True)


@scheduler_error_handler.register_error_handler(APIError)
async def scheduler_diary(e: APIError, child: Child):
    if e.code == 401:
        await admin_log("Проблема 401 в scheduler")
        await re_auth(e, child.vk_id)

    if not e.resp.ok:  # if server is not working
        return  # ignore

    logger.warning(f"Server error {e}")
    await admin_log(f"Ошибка в scheduler(1) у @id{child.vk_id}")


@scheduler_error_handler.register_error_handler(TimeoutError, ClientError)
async def scheduler_aiohttp_timeout(e: Union[TimeoutError, ClientError], _):
    logger.info(f"Server error {e}")


@scheduler_error_handler.register_undefined_error_handler
async def scheduler(e: BaseException, child: Child):
    logger.exception(f"Undefined error {e}")
    await admin_log(f"Ошибка в scheduler(undefined) у @id{child.vk_id}")
