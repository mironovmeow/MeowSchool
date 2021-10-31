from vkbottle.bot import Blueprint
from vkbottle_callback import MessageEvent, MessageEventLabeler
from vkbottle_callback.rules import PeerRule as MessageEventPeerRule

from bot import keyboards
from bot.blueprints.other import AuthState, today
from bot.error_handler import callback_error_handler
from diary import DiaryApi

labeler = MessageEventLabeler()
labeler.auto_rules = [MessageEventPeerRule(False)]

bp = Blueprint(name="PrivateMessageEvent", labeler=labeler)


@labeler.message_event(
    payload_map={"keyboard": str, "date": str},
    payload_contains={"keyboard": "diary"},
    state=AuthState.AUTH
)
@callback_error_handler.wraps_error_handler()
async def callback_diary_handler(event: MessageEvent):
    api: DiaryApi = event.state_peer.payload["api"]
    payload = event.get_payload_json()
    date: str = payload['date']
    diary = await api.diary(date)
    await event.edit_message(
        message=diary.info(),
        keyboard=keyboards.diary_week(date)
    )


@labeler.message_event(
    payload_map={"keyboard": str, "more": bool, "count": bool},
    payload_contains={"keyboard": "marks"},
    state=AuthState.AUTH
)
@callback_error_handler.wraps_error_handler()
async def callback_marks_handler(event: MessageEvent):
    api: DiaryApi = event.state_peer.payload["api"]
    payload = event.get_payload_json()
    more: bool = payload["more"]
    count: bool = payload["count"]
    if count:
        marks = await api.lessons_scores(today(), "")
        text = marks.info()
    else:
        marks = await api.progress_average(today())
        text = marks.info(more)
    await event.edit_message(
        message=text,
        keyboard=keyboards.marks_stats(more, count)
    )


# empty handler

@labeler.message_event()
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
