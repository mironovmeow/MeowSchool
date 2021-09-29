from loguru import logger
from vkbottle import ErrorHandler, VKAPIError, GroupTypes
from vkbottle.bot import Message

from bot.callback import show_snackbar
from diary.types import APIError

error_handler = ErrorHandler(redirect_arguments=True)
vk_error_handler = ErrorHandler()  # todo


@error_handler.register_error_handler(APIError)
async def exc_message_handler_diary_api(e: APIError, m: Message):
    if not e.resp.ok:
        if e.resp.status == 401:
            logger.info(f"Re-auth {m.peer_id}")
            await m.answer("Проблемы с авторизацией. Необходимо переподключиться")  # todo
        logger.warning(f"Server error {e.resp.status}")
        await m.answer("Временные неполадки с сервером. Повторите попытку позже")

    if not e.json_success:
        logger.warning(f"Server error {e.resp.status} {await e.resp.json()}")
        await m.answer("Временные неполадки с сервером. Повторите попытку позже")
    await e.session.close()


@error_handler.register_error_handler(VKAPIError())
async def exc_message_handler_vk_api(e: VKAPIError, m: Message):
    logger.warning(f"VKApi error {e}")
    await m.answer("Временные неполадки с сервером. Повторите попытку позже")


@error_handler.register_undefined_error_handler()
async def exc_message_handler(e: BaseException, m: Message):
    logger.warning(f"Undefined error {e}")
    await m.answer("Временные неполадки с сервером. Повторите попытку позже")


callback_error_handler = ErrorHandler(redirect_arguments=True)


@callback_error_handler.register_error_handler(APIError)
async def exc_callback_handler_diary_api(e: APIError, event: GroupTypes.MessageEvent):
    if not e.resp.ok:
        if e.resp.status == 401:
            logger.info(f"Re-auth {event.object.user_id}")
            await show_snackbar(event, "Проблемы с авторизацией. Необходимо переподключиться")  # todo
        logger.warning(f"Server error {e.resp.status}")
        await show_snackbar(event, "Временные неполадки с сервером. Повторите попытку позже")

    if not e.json_success:
        logger.warning(f"Server error {e.resp.status} {await e.resp.json()}")
        await show_snackbar(event, "Временные неполадки с сервером. Повторите попытку позже")
    await e.session.close()


@callback_error_handler.register_error_handler(VKAPIError(909))
async def exc_callback_handler_vk_api(e: VKAPIError, event: GroupTypes.MessageEvent):
    logger.warning(f"VKApi edit message error {e}")
    await show_snackbar(event, "Сообщение слишком старое. Воспользуйтесь меню снизу")


@callback_error_handler.register_error_handler(VKAPIError())
async def exc_callback_handler_vk_api(e: VKAPIError, event: GroupTypes.MessageEvent):
    logger.warning(f"VKApi error {e}")
    await show_snackbar(event, "Временные неполадки с сервером. Повторите попытку позже")


@callback_error_handler.register_undefined_error_handler()
async def exc_callback_handler(e: BaseException, event: GroupTypes.MessageEvent):
    logger.warning(f"Undefined error {e}")
    await show_snackbar(event, "Временные неполадки с сервером. Повторите попытку позже")
