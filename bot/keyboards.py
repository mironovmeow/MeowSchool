import datetime

from vkbottle.tools import Callback, Keyboard, KeyboardButtonColor, Text

SECONDARY = KeyboardButtonColor.SECONDARY


# keyboard for get diary and select day
def diary_week(date_str: str) -> str:
    today_date = datetime.date.today()
    user_date = datetime.date(*map(int, date_str.split(".")[::-1]))
    keyboard = Keyboard(inline=True)

    # add days in one week
    for i in range(0, 3):
        date = (user_date - datetime.timedelta(days=user_date.weekday() - i)).strftime("%d.%m.%Y")
        if user_date.weekday() == i:
            color = KeyboardButtonColor.POSITIVE
        elif today_date.strftime("%d.%m.%Y") == date:
            color = KeyboardButtonColor.PRIMARY
        else:
            color = SECONDARY
        keyboard.add(Callback(
            date, {"keyboard": "diary", "date": date}
        ), color)

    keyboard.row()

    for i in range(3, 6):
        date = (user_date - datetime.timedelta(days=user_date.weekday() - i)).strftime("%d.%m.%Y")
        if user_date.weekday() == i:
            color = KeyboardButtonColor.POSITIVE
        elif today_date.strftime("%d.%m.%Y") == date:
            color = KeyboardButtonColor.PRIMARY
        else:
            color = SECONDARY
        keyboard.add(Callback(
            date, {"keyboard": "diary", "date": date}
        ), color)

    keyboard.row()

    # add week control menu
    keyboard.add(Callback(
        "➖Неделя", {"keyboard": "diary", "date": (user_date - datetime.timedelta(weeks=1)).strftime("%d.%m.%Y")}
    ), SECONDARY)
    keyboard.add(Callback(
        "➕Неделя", {"keyboard": "diary", "date": (user_date + datetime.timedelta(weeks=1)).strftime("%d.%m.%Y")}
    ), SECONDARY)

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


def marks_stats(date: str, more: bool = False, count: bool = False) -> str:
    keyboard = Keyboard(inline=True)
    if count:
        keyboard.add(Callback(
            "📈 Средний балл",
            {"keyboard": "marks", "date": date, "more": more, "count": False}
        ), SECONDARY)
    else:
        keyboard.add(Callback(
            "🔢 Статистика по оценкам",
            {"keyboard": "marks", "date": date, "more": more, "count": True}
        ), SECONDARY)

        if more:
            keyboard.add(Callback(
                "🔘 Скрыть",
                {"keyboard": "marks", "date": date, "more": False, "count": count}
            ), SECONDARY)
        else:
            keyboard.add(Callback(
                "⚪ Подробнее",
                {"keyboard": "marks", "date": date, "more": True, "count": count}
            ), SECONDARY)
    return keyboard.get_json()
