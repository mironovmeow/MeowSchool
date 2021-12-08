"""
MessageEvent integration (all message_event handler, chat and private)
"""
from typing import List, Union

from vkbottle import ABCRule, BaseStateGroup, GroupEventType
from vkbottle.bot import Blueprint, MessageEvent
from vkbottle.dispatch.dispenser import get_state_repr

from bot import keyboard
from bot.db import Child, User
from bot.error_handler import callback_error_handler
from diary import DiaryApi
from . import scheduler
from .other import AuthState

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
    payload_map={"date": str, "child": int, "lesson": int},
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
    payload_map={"date": str, "child": int},
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
    payload_map={"date": str, "count": bool, "child": int},
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


async def change_child_marks(child: Child) -> str:
    if child.marks == 0:
        await scheduler.add(child)
        child.marks = 1
        text = "🔔 Уведомления об оценках включены"
    elif child.marks == 1:
        await scheduler.delete(child)
        child.marks = 0
        text = "🔕 Уведомления об оценках выключены"
    else:
        text = "🚧 Пока нельзя выключить донатные уведомления"
    await child.save()
    return text


@bp.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent,
    StateRule(AuthState.AUTH),
    payload_contains={"keyboard": "settings", "settings": "marks_child_select"}
)
async def callback_settings_marks_child_handler(event: MessageEvent):
    state_peer = await bp.state_dispenser.get(event.peer_id)
    api: DiaryApi = state_peer.payload["api"]
    user: User = state_peer.payload["user"]

    child_id = event.get_payload_json().get("child_id")
    if child_id and type(child_id) == int:
        await event.show_snackbar(await change_child_marks(user.children[child_id]))
    await event.edit_message(
        message="⚙ Настройки уведомлений об оценках",
        keyboard=keyboard.settings_marks(user, api.user.children)
    )


@bp.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent,
    StateRule(AuthState.AUTH),
    payload_map={"child_id": int},
    payload_contains={"keyboard": "settings", "settings": "marks"}
)
async def callback_settings_marks_handler(event: MessageEvent):
    child_id = event.get_payload_json()["child_id"]

    state_peer = await bp.state_dispenser.get(event.peer_id)
    user: User = state_peer.payload["user"]
    child = user.children[child_id]

    await event.show_snackbar(await change_child_marks(user.children[child_id]))
    await event.edit_message(
        message="⚙ Настройки",
        keyboard=keyboard.settings(child=child)
    )


@bp.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent,
    StateRule(AuthState.AUTH),
    payload_contains={"keyboard": "settings", "settings": "marks"}
)
async def callback_settings_handler(event: MessageEvent):
    state_peer = await bp.state_dispenser.get(event.peer_id)
    user: User = state_peer.payload["user"]

    await event.edit_message(
        message="⚙ Настройки",
        keyboard=keyboard.settings(user)
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
