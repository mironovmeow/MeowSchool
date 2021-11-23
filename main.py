import asyncio
import atexit

from bot import admin_log, auth_users_and_chats, bot, close, start_up
from diary import DiaryApi


async def _close_session():
    await admin_log("Система отключается.")
    await close()
    for state_peer in bot.state_dispenser.dictionary.values():
        api: DiaryApi = state_peer.payload.get("api")
        if api:  # not None
            await api.close()


@atexit.register
def close_session():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(_close_session())
    print("\nPlease, reboot me ^-^\n")


if __name__ == '__main__':
    bot.loop.run_until_complete(start_up())
    bot.loop.run_until_complete(auth_users_and_chats())
    bot.run_forever()
