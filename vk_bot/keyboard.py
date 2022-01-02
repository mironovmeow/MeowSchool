"""Keyboards module"""
import datetime
from typing import List

from vkbottle.tools import Callback, Keyboard, KeyboardButtonColor, Text

from diary.types import ChildObject, DiaryLessonObject
from .db import User

white = KeyboardButtonColor.SECONDARY
green = KeyboardButtonColor.POSITIVE
blue = KeyboardButtonColor.PRIMARY
red = KeyboardButtonColor.NEGATIVE


# diary with 6 days and date selector
def diary_week(date_str: str, children: List[ChildObject], child_id: int = 0) -> str:
    today_date = datetime.date.today()
    user_date = datetime.date(*map(int, date_str.split(".")[::-1]))
    keyboard = Keyboard(inline=True)

    # add days in one week
    for i in range(6):
        if i % 3 == 0:
            keyboard.row()

        date = (user_date - datetime.timedelta(days=user_date.weekday() - i)).strftime("%d.%m.%Y")
        if user_date.weekday() == i:
            color = green
        elif today_date.strftime("%d.%m.%Y") == date:
            color = blue
        else:
            color = white
        keyboard.add(Callback(
            date,
            {"keyboard": "diary", "date": date, "child": child_id}
        ), color)

    keyboard.row()

    # add week control menu
    keyboard.add(Callback(
        "➖Неделя",
        {
            "keyboard": "diary",
            "date": (user_date - datetime.timedelta(weeks=1)).strftime("%d.%m.%Y"),
            "child": child_id
        }
    ), white)
    keyboard.add(Callback(
        "➕Неделя",
        {
            "keyboard": "diary",
            "date": (user_date + datetime.timedelta(weeks=1)).strftime("%d.%m.%Y"),
            "child": child_id
        }
    ), white)

    keyboard.row()
    keyboard.add(Callback(
        "Подробнее", {"keyboard": "diary", "date": date_str, "child": child_id, "lesson": 0}
    ), white)

    # add user select
    if len(children) > 1:
        for e, child in enumerate(children):
            keyboard.row()
            keyboard.add(Callback(
                child.name,
                {"keyboard": "diary", "date": date_str, "child": e}
            ), green if e == child_id else white)

    return keyboard.get_json()


# diary with lessons and near date selector
# todo refactor buttons and rows limit
def diary_day(
        date_str: str,
        lessons: List[DiaryLessonObject],
        lesson_id: int = 0,
        child_id: int = 0
):
    user_date = datetime.date(*map(int, date_str.split(".")[::-1]))
    keyboard = Keyboard(inline=True)

    # add lesson select
    if len(lessons) > 0:
        for lesson_index, lesson in enumerate(lessons[:9]):  # workaround. 10 buttons max
            keyboard.add(Callback(
                lesson.discipline[:40],  # workaround. label should be not more than 40 letters
                {"keyboard": "diary", "date": date_str, "child": child_id, "lesson": lesson_index}
            ), green if lesson_index == lesson_id else white)
            if lesson_index % 2 == 1:
                keyboard.row()
    if len(lessons[:9]) % 2 == 1:
        keyboard.row()

    if len(lessons) <= 7:  # workaround. 10 buttons max
        # add day control menu
        keyboard.add(Callback(
            "➖День",
            {
                "keyboard": "diary",
                "date": (user_date - datetime.timedelta(days=1)).strftime("%d.%m.%Y"),
                "child": child_id,
                "lesson": 0
            }
        ), white)
        keyboard.add(Callback(
            "➕День",
            {
                "keyboard": "diary",
                "date": (user_date + datetime.timedelta(days=1)).strftime("%d.%m.%Y"),
                "child": child_id,
                "lesson": 0
            }
        ), white)

    keyboard.row()
    keyboard.add(Callback(
        "Скрыть", {"keyboard": "diary", "date": date_str, "child": child_id}
    ), white)

    # no user select. workaround. 10 buttons max

    return keyboard.get_json()


# marks menu
def marks_stats(date: str, children: List[ChildObject], count: bool = False, child_id: int = 0) -> str:
    keyboard = Keyboard(inline=True)
    if count:
        keyboard.add(Callback(
            "📈 Средний балл",
            {"keyboard": "marks", "date": date, "count": False, "child": child_id}
        ), white)
    else:
        keyboard.add(Callback(
            "🔢 Статистика по оценкам",
            {"keyboard": "marks", "date": date, "count": True, "child": child_id}
        ), white)

    # add user select
    if len(children) > 1:
        for e, child in enumerate(children):
            keyboard.row()
            keyboard.add(Callback(
                child.name,
                {"keyboard": "marks", "date": date, "count": count, "child": e}
            ), green if e == child_id else white)

    return keyboard.get_json()


MENU = (
    Keyboard()
    .add(Text("📗Дневник", payload={"keyboard": "menu", "menu": "diary"}), white)
    .add(Text("🔢Оценки", payload={"keyboard": "menu", "menu": "marks"}), white)
    .row()
    .add(Text("⚙Настройки", payload={"keyboard": "menu", "menu": "settings"}), white)
    .get_json()
)

EMPTY = Keyboard().get_json()


def settings(user: User):
    keyboard = Keyboard(inline=True)
    if user and len(user.children) == 1:
        child = user.children[0]
        keyboard.add(
            Callback("🔢Оценки", payload={"keyboard": "settings", "settings": "marks", "child_id": child.child_id}),
            green if child.marks_notify else white
        )
    else:
        keyboard.add(Callback("🔢Оценки", payload={"keyboard": "settings", "settings": "marks_child_select"}), blue)

    if user.refry_user is None:
        keyboard.row()
        keyboard.add(Callback("🎁Активировать реф.код", payload={"keyboard": "settings", "settings": "ref_code"}), blue)

    keyboard.row()
    keyboard.add(Callback("⚠️Удалить аккаунт", payload={"keyboard": "settings", "settings": "delete"}), red)
    return keyboard.get_json()


# todo refactor buttons and rows limit
def settings_marks(user: User, children: List[ChildObject]):
    keyboard = Keyboard(inline=True)

    for child_index, child in enumerate(user.children[:9]):  # workaround. 10 buttons max
        child_api = children[child_index]
        keyboard.add(Callback(
            child_api.name[:40],  # workaround. label should be not more than 40 letters
            {"keyboard": "settings", "settings": "marks_child_select", "child_id": child.child_id}
        ), green if child.marks > 0 else white)
        if child_index % 2 == 1:
            keyboard.row()
    if len(user.children[:9]) % 2 == 1:
        keyboard.row()  # workaround. 6 rows max
    keyboard.add(Callback("Вернуться", {"keyboard": "settings"}))
    return keyboard.get_json()


REF_CODE_BACK = (
    Keyboard(inline=True)
    .add(Callback("⚙Назад", payload={"ref_code": "settings"}), white)
    .get_json()
)


DELETE_VERIFY = (
    Keyboard(inline=True)
    .add(Callback("⚠️Да, удалить аккаунт", payload={"keyboard": "settings", "settings": "delete_verify"}), red)
    .row()
    .add(Callback("⚙Назад", payload={"keyboard": "settings"}), white)
    .get_json()
)
