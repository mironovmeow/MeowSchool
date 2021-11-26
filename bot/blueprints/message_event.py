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
    payload_map={"keyboard": str, "date": str, "child": int, "lesson": int},
    payload_contains={"keyboard": "diary"},
    state=AuthState.AUTH
)
@callback_error_handler.catch
async def callback_diary_handler(event: MessageEvent):
    api: DiaryApi = event.state_peer.payload["api"]
    payload = event.get_payload_json()
    date: str = payload["date"]
    child: int = payload["child"]
    lesson_index: int = payload["lesson"]
    diary = await api.diary(date, child=child)
    if diary.days[0].lessons is not None and len(diary.days[0].lessons) > 0:
        lesson = diary.days[0].lessons[lesson_index]
        await event.edit_message(
            message=lesson.info(event.peer_id != event.user_id, True),
            keyboard=keyboards.diary_day(date, diary.days[0].lessons, api.user.children, lesson_index, child)
        )
    else:
        await event.edit_message(
            message=diary.days[0].kind,
            keyboard=keyboards.diary_day(date, [], api.user.children, lesson_index, child)
        )


@labeler.message_event(
    payload_map={"keyboard": str, "date": str, "child": int},
    payload_contains={"keyboard": "diary"},
    state=AuthState.AUTH
)
@callback_error_handler.catch
async def callback_diary_handler(event: MessageEvent):
    api: DiaryApi = event.state_peer.payload["api"]
    payload = event.get_payload_json()
    date: str = payload["date"]
    child: int = payload["child"]
    diary = await api.diary(date, child=child)
    await event.edit_message(
        message=diary.info(event.peer_id != event.user_id),
        keyboard=keyboards.diary_week(date, api.user.children, child)
    )


# backward compatibility
@labeler.message_event(
    payload_map={"keyboard": str, "date": str},
    payload_contains={"keyboard": "diary"},
    state=AuthState.AUTH
)
@callback_error_handler.catch
async def callback_marks_handler(event: MessageEvent):
    api: DiaryApi = event.state_peer.payload["api"]
    payload = event.get_payload_json()
    date: str = payload["date"]
    child: int = 0
    diary = await api.diary(date, child=child)
    await event.edit_message(
        message=diary.info(event.peer_id != event.user_id),
        keyboard=keyboards.diary_week(date, api.user.children, child)
    )


@labeler.message_event(
    payload_map={"keyboard": str, "date": str, "count": bool, "child": int},
    payload_contains={"keyboard": "marks"},
    state=AuthState.AUTH
)
@callback_error_handler.catch
async def callback_marks_handler(event: MessageEvent):
    api: DiaryApi = event.state_peer.payload["api"]
    payload = event.get_payload_json()
    date: str = payload["date"]
    count: bool = payload["count"]
    child: int = payload["child"]
    if count:
        marks = await api.lessons_scores(date, child=child)
        text = marks.info()
    else:
        marks = await api.progress_average(date, child=child)
        text = marks.info()
    await event.edit_message(
        message=text,
        keyboard=keyboards.marks_stats(date, api.user.children, count, child)
    )


# backward compatibility
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
    count: bool = payload["count"]
    child: int = 0
    if count:
        marks = await api.lessons_scores(date, child=child)
        text = marks.info()
    else:
        marks = await api.progress_average(date, child=child)
        text = marks.info()
    await event.edit_message(
        message=text,
        keyboard=keyboards.marks_stats(date, api.user.children, count, child)
    )


# empty handler

@labeler.message_event()
@callback_error_handler.catch
async def empty_callback_handler(event: MessageEvent):
    if event.state_peer is not None and event.state_peer.state == get_state_repr(AuthState.AUTH):
        await event.show_snackbar("🚧 Странно, но кнопка не найдена. Повторите попытку позже")
    else:
        await event.show_snackbar("🚧 Пройдите повторную авторизацию через команду /начать (/start)")
