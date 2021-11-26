import datetime
from typing import List

from vkbottle.tools import Callback, Keyboard, KeyboardButtonColor, Text

from diary import ChildObject, DiaryLessonObject

SECONDARY = KeyboardButtonColor.SECONDARY


# keyboard for get diary and select day
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
            color = KeyboardButtonColor.POSITIVE
        elif today_date.strftime("%d.%m.%Y") == date:
            color = KeyboardButtonColor.PRIMARY
        else:
            color = SECONDARY
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
    ), SECONDARY)
    keyboard.add(Callback(
        "➕Неделя",
        {
            "keyboard": "diary",
            "date": (user_date + datetime.timedelta(weeks=1)).strftime("%d.%m.%Y"),
            "child": child_id
        }
    ), SECONDARY)

    keyboard.row()
    keyboard.add(Callback(
        "Подробнее", {"keyboard": "diary", "date": date_str, "child": child_id, "lesson": 0}
    ), SECONDARY)

    # add user select
    if len(children) > 1:
        for e, child in enumerate(children):
            keyboard.row()
            keyboard.add(Callback(
                child.name,
                {"keyboard": "diary", "date": date_str, "child": e}
            ), KeyboardButtonColor.POSITIVE if e == child_id else SECONDARY)

    return keyboard.get_json()


def diary_day(
        date_str: str,
        lessons: List[DiaryLessonObject],
        children: List[ChildObject],
        lesson_id: int = 0,
        child_id: int = 0
):
    user_date = datetime.date(*map(int, date_str.split(".")[::-1]))
    keyboard = Keyboard(inline=True)

    # add lesson select
    if len(lessons) > 1:
        for e, lesson in enumerate(lessons[:9]):  # workaround. 10 buttons max
            keyboard.add(Callback(
                lesson.discipline[:40],  # workaround. label should be not more than 40 letters
                {"keyboard": "diary", "date": date_str, "child": child_id, "lesson": e}
            ), KeyboardButtonColor.POSITIVE if e == lesson_id else SECONDARY)
            if e % 2 == 1:
                keyboard.row()
    if len(lessons) % 2 == 1:
        keyboard.row()  # workaround. 10 buttons max

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
        ), SECONDARY)
        keyboard.add(Callback(
            "➕День",
            {
                "keyboard": "diary",
                "date": (user_date + datetime.timedelta(days=1)).strftime("%d.%m.%Y"),
                "child": child_id,
                "lesson": 0
            }
        ), SECONDARY)

    keyboard.row()
    keyboard.add(Callback(
        "Скрыть", {"keyboard": "diary", "date": date_str, "child": child_id}
    ), SECONDARY)

    # no user select. workaround. 10 buttons max

    return keyboard.get_json()


def menu() -> str:
    keyboard = (
        Keyboard()
        .add(Text("📗Дневник", payload={"keyboard": "menu", "menu": "diary"}), SECONDARY)
        .add(Text("🔢Оценки", payload={"keyboard": "menu", "menu": "marks"}), SECONDARY)
        .row()
        .add(Text("⚙Настройки", payload={"keyboard": "menu", "menu": "settings"}), SECONDARY)
    )
    return keyboard.get_json()


def empty() -> str:
    return Keyboard().get_json()


def marks_stats(date: str, children: List[ChildObject], count: bool = False, child_id: int = 0) -> str:
    keyboard = Keyboard(inline=True)
    if count:
        keyboard.add(Callback(
            "📈 Средний балл",
            {"keyboard": "marks", "date": date, "count": False, "child": child_id}
        ), SECONDARY)
    else:
        keyboard.add(Callback(
            "🔢 Статистика по оценкам",
            {"keyboard": "marks", "date": date, "count": True, "child": child_id}
        ), SECONDARY)

    # add user select
    if len(children) > 1:
        for e, child in enumerate(children):
            keyboard.row()
            keyboard.add(Callback(
                child.name,
                {"keyboard": "marks", "date": date, "count": count, "child": e}
            ), KeyboardButtonColor.POSITIVE if e == child_id else SECONDARY)

    return keyboard.get_json()
