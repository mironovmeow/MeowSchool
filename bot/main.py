import sys

from vkbottle.bot import Bot

from bot.blueprints import bp_list
from bot.error_handler import vk_error_handler
from vkbottle_meow import MessageEventLabeler

if len(sys.argv) < 2:
    raise ValueError("Token is undefined")
TOKEN = sys.argv[1]


labeler = MessageEventLabeler()

bot = Bot(TOKEN, labeler=labeler, error_handler=vk_error_handler)


for bp in bp_list:
    bp.load(bot)
