from vkbottle.bot import Blueprint

from bot import keyboards
from bot.blueprints.other import AuthState, today
from bot.error_handler import callback_error_handler
from bot.rules import MessageEventKeyboardRule
from diary import DiaryApi
from vkbottle_meow import MessageEvent, MessageEventLabeler
from vkbottle_meow.rules import PeerRule as MessageEventPeerRule, StateRule as MessageEventStateRule

labeler = MessageEventLabeler(custom_rules={
    "keyboard": MessageEventKeyboardRule,
    "state": MessageEventStateRule
})
labeler.auto_rules = [MessageEventPeerRule(False)]

bp = Blueprint(name="PrivateMessageEvent", labeler=labeler)


@bp.on.message_event(keyboard="diary", state=AuthState.AUTH)
@callback_error_handler.wraps_error_handler()
async def callback_diary_handler(event: MessageEvent):
    api: DiaryApi = event.state_peer.payload["api"]
    diary = await api.diary(event.payload.get('date'))
    await bp.api.messages.edit(
        peer_id=event.peer_id,
        conversation_message_id=event.conversation_message_id,
        message=diary.info(),
        keyboard=keyboards.diary_week(event.payload.get('date'))
    )


@bp.on.message_event(keyboard="marks", state=AuthState.AUTH)
@callback_error_handler.wraps_error_handler()
async def callback_marks_handler(event: MessageEvent):
    api: DiaryApi = event.state_peer.payload["api"]
    more: bool = event.payload.get("more")
    count: bool = event.payload.get("count")
    if count:
        marks = await api.lessons_scores(today(), "")
        text = marks.info()
    else:
        marks = await api.progress_average(today())
        text = marks.info(more)
    await bp.api.messages.edit(
        peer_id=event.peer_id,
        conversation_message_id=event.conversation_message_id,
        message=text,
        keyboard=keyboards.marks_stats(more, count)
    )


# empty handler

@bp.on.message_event()
@callback_error_handler.wraps_error_handler()
async def empty_callback_handler(event: MessageEvent):
    if event.state_peer is not None and event.state_peer.state == AuthState.AUTH:
        await event.show_snackbar("Странно, но кнопка не найдена...")
    else:
        await bp.state_dispenser.set(event.peer_id, AuthState.LOGIN)
        await bp.api.messages.send(
            peer_id=event.peer_id,
            message="Добро пожаловать в сообщество \"Школьный бот\"!\n"
                    "Здесь можно узнать домашнее задание и оценки из sosh.mon-ra.ru\n"
                    "Для начало работы мне нужен логин и пароль от вышеуказанного сайта. "
                    "Отправь первым сообщением логин.",
            dont_parse_links=True,
            random_id=0
        )