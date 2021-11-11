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
        message=diary.info(),
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
        marks = await api.lessons_scores(date, "")
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
        await event.show_snackbar("Странно, но кнопка не найдена...\nВыполните команду ещё раз.")
    elif event.peer_id < 2000000000:  # if user
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
    else:
        await event.show_snackbar("Очень странная ошибка...")
