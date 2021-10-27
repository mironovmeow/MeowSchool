from vkbottle.bot import Blueprint
from vkbottle.dispatch.rules.bot import PeerRule, StateRule
from vkbottle.framework.bot import BotLabeler


labeler = BotLabeler(custom_rules={
    "state": StateRule
})
labeler.auto_rules = [PeerRule(True)]


bp = Blueprint(name="ChatMessage", labeler=labeler)
