"""
MessageEvent integration (all message_event handler, chat and private)
"""
from typing import List, Union

from vkbottle import ABCRule, BaseStateGroup, GroupEventType
from vkbottle.bot import Blueprint, MessageEvent
from vkbottle.dispatch.dispenser import get_state_repr

from bot import keyboard
from bot.blueprints.other import AuthState
from bot.error_handler import callback_error_handler
from diary import DiaryApi

bp = Blueprint(name="MessageEvent")


class StateRule(ABCRule[MessageEvent]):
    def __init__(self, state: Union[List["BaseStateGroup"], "BaseStateGroup"]):
        if not isinstance(state, list):
            state = [] if state is None else [state]
        self.state = [get_state_repr(s) for s in state]

    async def check(self, event: MessageEvent) -> bool:
        state_peer = await bp.state_dispenser.get(event.peer_id)
        if state_peer is None:
            return not self.state
        return state_peer.state in self.state


@bp.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent,
    StateRule(AuthState.AUTH),
    payload_map={"keyboard": str, "date": str, "child": int, "lesson": int},
    payload_contains={"keyboard": "diary"}
)
@callback_error_handler.catch
async def callback_diary_day_handler(event: MessageEvent):
    state_peer = await bp.state_dispenser.get(event.peer_id)
    api: DiaryApi = state_peer.payload["api"]
    payload = event.get_payload_json()
    date: str = payload["date"]
    child: int = payload["child"]
    lesson_index: int = payload["lesson"]
    diary = await api.diary(date, child=child)
    if diary.days[0].lessons is not None and len(diary.days[0].lessons) > 0:
        lesson = diary.days[0].lessons[lesson_index]
        await event.edit_message(
            message=lesson.info(event.peer_id != event.user_id, True),
            keyboard=keyboard.diary_day(date, diary.days[0].lessons, lesson_index, child)
        )
    else:
        await event.edit_message(
            message=diary.days[0].kind,
            keyboard=keyboard.diary_day(date, [], lesson_index, child)
        )


@bp.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent,
    StateRule(AuthState.AUTH),
    payload_map={"keyboard": str, "date": str, "child": int},
    payload_contains={"keyboard": "diary"}
)
@callback_error_handler.catch
async def callback_diary_week_handler(event: MessageEvent):
    state_peer = await bp.state_dispenser.get(event.peer_id)
    api: DiaryApi = state_peer.payload["api"]
    payload = event.get_payload_json()
    date: str = payload["date"]
    child: int = payload["child"]
    diary = await api.diary(date, child=child)
    await event.edit_message(
        message=diary.info(event.peer_id != event.user_id),
        keyboard=keyboard.diary_week(date, api.user.children, child)
    )


@bp.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent,
    StateRule(AuthState.AUTH),
    payload_map={"keyboard": str, "date": str, "count": bool, "child": int},
    payload_contains={"keyboard": "marks"}
)
@callback_error_handler.catch
async def callback_marks_handler(event: MessageEvent):
    state_peer = await bp.state_dispenser.get(event.peer_id)
    api: DiaryApi = state_peer.payload["api"]
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
        keyboard=keyboard.marks_stats(date, api.user.children, count, child)
    )


# empty handler
@bp.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent
)
@callback_error_handler.catch
async def empty_callback_handler(event: MessageEvent):
    if event.state_peer is not None and event.state_peer.state == get_state_repr(AuthState.AUTH):
        await event.show_snackbar("🚧 Странно, но кнопка не найдена. Повторите попытку позже")
    else:
        await event.show_snackbar("🚧 Пройдите повторную авторизацию через команду /начать (/start)")
