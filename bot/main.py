import sys

from vkbottle import LoopWrapper
from vkbottle.bot import Bot
from vkbottle_callback import MessageEventLabeler

from diary import DiaryApi
from . import start_up, auth_users_and_chats, admin_log, close, bp_list, vkbottle_error_handler

if len(sys.argv) < 2:
    raise ValueError("Token is undefined")
TOKEN = sys.argv[1]


async def _close_session():
    await admin_log("Система отключается.")
    await close()
    for state_peer in bot.state_dispenser.dictionary.values():
        api: DiaryApi = state_peer.payload.get("api")
        if api:  # not None
            await api.close()


labeler = MessageEventLabeler()
loop_wrapper = LoopWrapper(
    on_startup=[
        start_up(),
        auth_users_and_chats()
    ],
    on_shutdown=[
        _close_session()
    ]
)

bot = Bot(TOKEN, labeler=labeler, loop_wrapper=loop_wrapper, error_handler=vkbottle_error_handler)


for bp in bp_list:
    bp.load(bot)
