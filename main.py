import asyncio
import atexit

from bot import auth_in_private_message, bot
from bot.blueprints.admin import admin_log
from diary import DiaryApi


@atexit.register
def close_session():
    loop = asyncio.get_event_loop()
    loop.run_until_complete(admin_log("Система отключается."))
    for state_peer in bot.state_dispenser.dictionary.values():
        api: DiaryApi = state_peer.payload["api"]
        loop.run_until_complete(api.close())
    print("\n\nPlease, reboot me ^-^\n")


if __name__ == '__main__':
    bot.loop.run_until_complete(auth_in_private_message())
    bot.run_forever()
