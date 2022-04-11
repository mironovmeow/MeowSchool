from typing import List, Optional

from barsdiary.types import (
    DiaryDayObject,
    DiaryLessonObject,
    DiaryObject,
    LessonsScoreObject,
    ProgressAverageObject,
    ProgressDataObject,
    ScoreObject,
)


def _mark(marks: List[list]) -> str:  # for diary_lesson_info()
    if len(marks) == 0:  # no marks
        return ""
    marks_str = ""
    for mark_list in marks[0][len(marks[0]) // 2 :]:
        for mark_str in mark_list:
            if mark_str:
                marks_str += mark_str + "️⃣"  # use combinations of emoji
    return marks_str


def diary_lesson_info(obj: DiaryLessonObject, is_chat: bool, full: bool = False) -> str:
    homework_list = []
    for homework in obj.homework:
        if homework != "":
            homework_list.append("📗 " + homework)
    if homework_list:
        homework = "\n".join(homework_list)
    else:
        homework = "📙 Нет домашнего задания"

    if full:
        return (
            f"📚 {obj.discipline} {_mark(obj.marks) if is_chat else ''}\n"
            f"⌚ {obj.lesson[1]} ({obj.lesson[2]} -- {obj.lesson[3]})\n"
            f"👩‍🏫 {obj.teacher}\n"
            f"Тема: {obj.subject if obj.subject else 'Нет темы'}\n\n"
            f"{homework}\n\n"
            f"🏫 {obj.room}"
        )

    return (
        f"⌚ {obj.lesson[1]}: {obj.discipline} {_mark(obj.marks) if is_chat else ''}\n"
        f"{homework}"
    )


_day_of_week: List[str] = [
    "Понедельник",
    "Вторник",
    "Среда",
    "Четверг",
    "Пятница",
    "Суббота",
    "Воскресенье",
]


def diary_day_info(obj: DiaryDayObject, is_chat: bool, lesson_id: Optional[int] = None) -> str:
    text = f"📅 {_day_of_week[obj.date.weekday()]} [{obj.date_str}]\n\n"
    if not obj.lessons:
        text += obj.kind or ""
    elif lesson_id is None:
        text += "\n\n".join(diary_lesson_info(lesson, is_chat) for lesson in obj.lessons)
    else:
        text += diary_lesson_info(obj.lessons[lesson_id], is_chat, True)
    return text


def diary_info(obj: DiaryObject, is_chat: bool = False):
    return "\n\n".join(diary_day_info(day, is_chat) for day in obj.days)


def _bar(mark: float) -> str:  # for progress_data_info
    if mark < 1.5:
        return "⚫"
    elif mark < 2.5:
        return "🔴"
    elif mark < 3.5:
        return "🟠"
    elif mark < 4.5:
        return "🟡"
    else:
        return "🟢"


def progress_data_info(obj: ProgressDataObject):
    return "\n".join(
        f"{_bar(mark)} [{mark:.2f}] {subject}"
        for subject, mark in sorted((obj.data or {}).items(), key=lambda v: (-v[1], v[0]))
    )


def progress_average_info(obj: ProgressAverageObject) -> str:
    if obj.kind:
        return f"🚧 {obj.kind}"
    return f"📅 {obj.sub_period}\n\n{progress_data_info(obj.self)}"


def _get_score_stat(scores: List[ScoreObject]) -> str:
    stats = {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}
    for score in scores:
        for marks in score.marks.values():
            for mark in marks:
                stats[mark] += 1

    return "  ".join(f"{mark}⃣: {count}" for mark, count in stats.items())


def lesson_score_info(obj: LessonsScoreObject):
    if obj.data is None or len(obj.data) == 0:
        if obj.kind:
            return f"🚧 {obj.kind}"
        else:
            return f"📅 {obj.sub_period}"
    return f"📅 {obj.sub_period}\n\n" + "\n".join(
        f"{lesson}:\n{_get_score_stat(score)}" for lesson, score in obj.data.items()
    )
