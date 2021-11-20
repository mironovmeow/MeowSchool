import sys

from vkbottle.bot import Bot
from vkbottle_callback import MessageEventLabeler

from .blueprints import bp_list
from .error_handler import vkbottle_error_handler

if len(sys.argv) < 2:
    raise ValueError("Token is undefined")
TOKEN = sys.argv[1]


labeler = MessageEventLabeler()

bot = Bot(TOKEN, labeler=labeler, error_handler=vkbottle_error_handler)


for bp in bp_list:
    bp.load(bot)
