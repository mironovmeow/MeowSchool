from vkbottle.bot import Blueprint
from vkbottle.dispatch.rules.bot import FromPeerRule

from vkbottle_meow import MessageEventLabeler
from vkbottle_meow.rules import FromPeerRule as MessageEventFromPeerRule

ADMINS = [
    248525108,  # @mironovmeow      | Миронов Данил
]

is_admin = FromPeerRule(ADMINS)
event_is_admin = MessageEventFromPeerRule(ADMINS)

labeler = MessageEventLabeler()
bp = Blueprint(name="AdminMessage", labeler=labeler)


async def admin_log(
        text: str
):
    for peer_id in ADMINS:
        await bp.api.messages.send(
            message="Уведомление от системы!\n\n" + text,
            peer_id=peer_id,
            random_id=0
        )
