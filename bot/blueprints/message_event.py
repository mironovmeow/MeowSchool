from vkbottle.bot import Blueprint
from vkbottle.dispatch.dispenser import get_state_repr
from vkbottle_callback import MessageEvent, MessageEventLabeler

from bot import keyboards
from bot.blueprints.other import AuthState
from bot.error_handler import callback_error_handler
from diary import DiaryApi

labeler = MessageEventLabeler()

bp = Blueprint(name="MessageEvent", labeler=labeler)


@labeler.message_event(
    payload_map={"keyboard": str, "date": str},
    payload_contains={"keyboard": "diary"},
    state=AuthState.AUTH
)
@callback_error_handler.catch
async def callback_diary_handler(event: MessageEvent):
    api: DiaryApi = event.state_peer.payload["api"]
    payload = event.get_payload_json()
    date: str = payload['date']
    diary = await api.diary(date)
    await event.edit_message(
        message=diary.info(event.peer_id != event.user_id),
        keyboard=keyboards.diary_week(date)
    )


@labeler.message_event(
    payload_map={"keyboard": str, "date": str, "more": bool, "count": bool},
    payload_contains={"keyboard": "marks"},
    state=AuthState.AUTH
)
@callback_error_handler.catch
async def callback_marks_handler(event: MessageEvent):
    api: DiaryApi = event.state_peer.payload["api"]
    payload = event.get_payload_json()
    date: str = payload["date"]
    more: bool = payload["more"]
    count: bool = payload["count"]
    if count:
        marks = await api.lessons_scores(date)
        text = marks.info()
    else:
        marks = await api.progress_average(date)
        text = marks.info(more)
    await event.edit_message(
        message=text,
        keyboard=keyboards.marks_stats(date, more, count)
    )


# empty handler

@labeler.message_event()
@callback_error_handler.catch
async def empty_callback_handler(event: MessageEvent):
    if event.state_peer is not None and event.state_peer.state == get_state_repr(AuthState.AUTH):
        await event.show_snackbar("🚧 Странно, но кнопка не найдена. Повторите попытку позже")
    else:
        await event.show_snackbar("🚧 Пройдите повторную авторизацию через команду /начать (/start)")
