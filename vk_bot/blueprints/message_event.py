"""
MessageEvent integration (all message_event handler, chat and private)
"""
from typing import List, Union

from vkbottle import ABCRule, BaseStateGroup, GroupEventType
from vkbottle.bot import Blueprint, MessageEvent
from vkbottle.dispatch.dispenser import get_state_repr

from diary import DiaryApi
from vk_bot import keyboard
from vk_bot.db import Child, User
from vk_bot.error_handler import callback_error_handler
from . import scheduler
from .other import MeowState, admin_log

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
    StateRule(MeowState.NOT_AUTH),
)
@callback_error_handler.catch
async def not_auth_handler(event: MessageEvent):
    await event.show_snackbar("🚧 Тех. работы. Ожидайте")
    await admin_log(f"@id{event.peer_id} не авторизован")


@bp.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent,
    StateRule(MeowState.AUTH),
    payload_map={"date": str, "lesson": int},
    payload_contains={"keyboard": "diary"}
)
@callback_error_handler.catch
async def diary_day_handler(event: MessageEvent):
    state_peer = await bp.state_dispenser.get(event.peer_id)
    api: DiaryApi = state_peer.payload["api"]
    payload = event.payload
    date: str = payload["date"]
    child: int = state_peer.payload["child_id"]
    lesson_index: int = payload["lesson"]
    diary = await api.diary(date, child=child)
    if diary.days[0].lessons is not None and len(diary.days[0].lessons) > 0:
        lesson = diary.days[0].lessons[lesson_index]
        await event.edit_message(
            message=lesson.info(event.peer_id != event.user_id, True),
            keyboard=keyboard.diary_day(date, diary.days[0].lessons, lesson_index)
        )
    else:
        await event.edit_message(
            message=diary.days[0].kind,
            keyboard=keyboard.diary_day(date, [], lesson_index)
        )


@bp.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent,
    StateRule(MeowState.AUTH),
    payload_map={"date": str},
    payload_contains={"keyboard": "diary"}
)
@callback_error_handler.catch
async def diary_week_handler(event: MessageEvent):
    state_peer = await bp.state_dispenser.get(event.peer_id)
    api: DiaryApi = state_peer.payload["api"]
    payload = event.payload
    date: str = payload["date"]
    child: int = state_peer.payload["child_id"]
    diary = await api.diary(date, child=child)
    await event.edit_message(
        message=diary.info(event.peer_id != event.user_id),
        keyboard=keyboard.diary_week(date)
    )


@bp.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent,
    StateRule(MeowState.AUTH),
    payload_map={"date": str, "count": bool},
    payload_contains={"keyboard": "marks"}
)
@callback_error_handler.catch
async def marks_handler(event: MessageEvent):
    state_peer = await bp.state_dispenser.get(event.peer_id)
    api: DiaryApi = state_peer.payload["api"]
    payload = event.payload
    date: str = payload["date"]
    count: bool = payload["count"]
    child: int = state_peer.payload["child_id"]
    if count:
        marks = await api.lessons_scores(date, child=child)
        text = marks.info()
    else:
        marks = await api.progress_average(date, child=child)
        text = marks.info()
    await event.edit_message(
        message=text,
        keyboard=keyboard.marks_stats(date, count)
    )


async def change_child_marks(child: Child) -> str:
    if child.marks_notify:
        await scheduler.delete(child)
        child.marks_notify = False
        text = "🔔 Уведомления об оценках выключены"
    else:
        await scheduler.add(child)
        child.marks_notify = True
        text = "🔔 Уведомления об оценках включены"
    await child.save()
    return text


@bp.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent,
    StateRule(MeowState.AUTH),
    payload_contains={"keyboard": "settings", "settings": "marks_child_select"}
)
@callback_error_handler.catch
async def settings_marks_child_handler(event: MessageEvent):
    state_peer = await bp.state_dispenser.get(event.peer_id)
    api: DiaryApi = state_peer.payload["api"]
    user: User = state_peer.payload["user"]

    child_id = event.payload.get("child_id")
    if type(child_id) == int:
        await event.show_snackbar(await change_child_marks(user.children[child_id]))
    await event.edit_message(
        message="⚙ Настройки уведомлений об оценках",
        keyboard=keyboard.settings_marks(user, api.user.children)
    )


@bp.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent,
    StateRule(MeowState.AUTH),
    payload_map={"child_id": int},
    payload_contains={"keyboard": "settings", "settings": "marks"}
)
@callback_error_handler.catch
async def settings_marks_handler(event: MessageEvent):
    child_id = event.payload["child_id"]

    state_peer = await bp.state_dispenser.get(event.peer_id)
    user: User = state_peer.payload["user"]

    await event.show_snackbar(await change_child_marks(user.children[child_id]))
    await event.edit_message(
        message="⚙ Настройки",
        keyboard=keyboard.settings(user)
    )


@bp.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent,
    StateRule(MeowState.AUTH),
    payload_map={"child_id": int},
    payload_contains={"keyboard": "settings", "settings": "child_select"}
)
@callback_error_handler.catch
async def settings_child_select_handler(event: MessageEvent):
    child_id = event.payload["child_id"]

    state_peer = await bp.state_dispenser.get(event.peer_id)
    api: DiaryApi = state_peer.payload["api"]

    state_peer.payload["child_id"] = child_id

    await event.edit_message(
        message="⚙ Выбор ученика",
        keyboard=keyboard.settings_child_select(api.user.children, child_id)
    )


@bp.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent,
    StateRule(MeowState.AUTH),
    payload_contains={"keyboard": "settings", "settings": "child_select"}
)
@callback_error_handler.catch
async def settings_child_handler(event: MessageEvent):
    state_peer = await bp.state_dispenser.get(event.peer_id)
    api: DiaryApi = state_peer.payload["api"]

    await event.edit_message(
        message="⚙ Выбор ученика",
        keyboard=keyboard.settings_child_select(api.user.children, state_peer.payload["child_id"])
    )


@bp.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent,
    StateRule(MeowState.AUTH),
    payload_contains={"keyboard": "settings", "settings": "delete"}
)
@callback_error_handler.catch
async def user_delete_handler(event: MessageEvent):
    await event.show_snackbar("🚧 Вы уверены?")
    await event.edit_message(
        message="🚧 Вы уверены?",
        keyboard=keyboard.DELETE_VERIFY
    )


@bp.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent,
    StateRule(MeowState.AUTH),
    payload_contains={"keyboard": "settings", "settings": "delete_verify"}
)
@callback_error_handler.catch
async def delete_verify_handler(event: MessageEvent):
    state_peer = await bp.state_dispenser.get(event.peer_id)
    user: User = state_peer.payload["user"]
    for chat in user.chats:
        await bp.api.messages.send(
            peer_id=chat.peer_id,
            random_id=0,
            message="🚧 Профиль, который активировал беседу, был удалён.\n"
                    "🔒 Напишите /начать (/start), что бы авторизовать беседу"
        )
        await bp.state_dispenser.delete(chat.peer_id)
    await user.delete()

    api: DiaryApi = state_peer.payload["api"]
    await api.logout()
    await api.close_session()

    await bp.state_dispenser.delete(event.peer_id)

    await event.edit_message("🚧 Выполнено")
    await event.send_message(
        "🔸 Если захотите вернуться, напишите что-нибудь снова",
        keyboard=keyboard.EMPTY
    )
    await admin_log(f"Пользователь @id{event.peer_id} удалился")


@bp.on.raw_event(
    GroupEventType.MESSAGE_EVENT,
    MessageEvent,
    StateRule(MeowState.AUTH),
    payload_contains={"keyboard": "settings"}
)
@callback_error_handler.catch
async def settings_handler(event: MessageEvent):
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
    if event.state_peer is not None and event.state_peer.state == get_state_repr(MeowState.AUTH):
        await event.show_snackbar("🚧 Странно, но кнопка не найдена. Повторите попытку позже")
    else:
        await event.show_snackbar("🚧 Пройдите повторную авторизацию через команду /начать (/start)")
