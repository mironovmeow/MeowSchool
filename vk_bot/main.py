import sys

from barsdiary.aio import DiaryApi
from loguru import logger
from vkbottle import LoopWrapper
from vkbottle.bot import Bot

from .blueprints import admin, chat, message_event, other, private, scheduler
from .db import close, start_up
from .error_handler import vkbottle_error_handler

if len(sys.argv) < 2:
    raise ValueError("Token is undefined")
TOKEN = sys.argv[1]

# logger.remove()

logger.add("full.log", encoding="utf8", rotation="24h")  # ...
# logger.add("vk_api.log", encoding="utf8", filter="vkbottle.api.api")
# logger.add("diary_api.log", encoding="utf8", filter="diary.api")
logger.add("error.log", encoding="utf8", level=40, rotation="10 MB")
logger.disable("vkbottle.framework.bot.bot")
logger.disable("vkbottle.polling.bot_polling")
logger.disable("vk_bot.blueprints.scheduler")


async def _close_session():
    await other.admin_log("Система отключается.")
    scheduler.stop()
    await close()
    for peer_id, state_peer in bot.state_dispenser.dictionary.items():
        if peer_id < 2000000000:  # if user
            api: DiaryApi = state_peer.payload.get("api")
            if api:  # not None
                await api.close_session()


loop_wrapper = LoopWrapper(
    on_startup=[start_up(), other.auth_users_and_chats(), scheduler.start()],
    on_shutdown=[_close_session()],
)

bot = Bot(TOKEN, loop_wrapper=loop_wrapper, error_handler=vkbottle_error_handler)

bps = [admin.bp, chat.bp, private.bp, message_event.bp, other.bp, scheduler.bp]

for bp in bps:
    bp.load(bot)
