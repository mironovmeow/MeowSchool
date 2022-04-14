"""
Schedulers module (marks notification)
"""
import datetime
from typing import Dict, List, Optional, Tuple

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from barsdiary.aio import DiaryApi
from vkbottle.bot import Blueprint
from vkbottle.modules import logger

from vk_bot.blueprints.other import admin_log
from vk_bot.db import Child, User, select, session
from vk_bot.error_handler import scheduler_error_handler


class Marks:
    def __init__(self, lesson: str, date: str, text: str, mark: str):
        self.lesson = lesson
        self.date = date
        self.text = text
        self.mark = mark

    @classmethod
    async def from_api(cls, child: Child) -> Tuple[Dict["Marks", int], Optional[str]]:
        state_peer = await bp.state_dispenser.get(child.vk_id)
        if not state_peer:
            return {}, None
        api: DiaryApi = state_peer.payload["api"]
        if api.closed:
            return DATA[child]  # wait for re-auth

        lessons_score = await api.lessons_scores(_today(), child=child.child_id)
        ans: Dict[Marks, int] = {}
        for lesson, data in lessons_score.data.items():
            for score in data:
                for text, marks_list in score.marks.items():
                    for mark_int in marks_list:
                        marks = cls(lesson, score.date, text, mark_int)
                        ans.setdefault(marks, 0)
                        ans[marks] += 1
        return ans, lessons_score.sub_period

    def __hash__(self):
        return hash((self.lesson, self.date, self.text, self.mark))

    def __eq__(self, other):
        if isinstance(other, Marks):
            return (
                self.lesson == other.lesson
                and self.date == other.date
                and self.text == other.text
                and self.mark == other.mark
            )
        return False


childs_marks = select(Child).join(User).where(Child.marks_notify.is_(True))

scheduler = AsyncIOScheduler()
bp = Blueprint(name="Scheduler")  # use for message_send

DATA: Dict[Child, Tuple[Dict[Marks, int], Optional[str]]] = {}


def _today() -> str:
    return datetime.date.today().strftime("%d.%m.%Y")


@scheduler_error_handler.catch
async def marks_job(child: Child):
    old_marks, old_period = DATA[child]
    new_marks, new_period = await Marks.from_api(child)

    if old_period != new_period:  # new period
        await bp.api.messages.send(
            child.vk_id, message=f"🔔 Изменение периода в оценках: {new_period}.\n", random_id=0
        )
        old_marks = new_marks
        DATA[child] = ({}, new_period)

    changed_marks: Dict[str, Dict[str, List[str]]] = {}  # date: {lesson: [information]}

    mark_keys = old_marks.keys() | new_marks.keys()

    for mark in mark_keys:
        old_count = old_marks.get(mark, 0)
        new_count = new_marks.get(mark, 0)

        if new_count > old_count:  # new mark
            changed_marks.setdefault(mark.date, {})
            changed_marks[mark.date].setdefault(mark.lesson, [])
            for _ in range(new_count - old_count):
                changed_marks[mark.date][mark.lesson].append(f"✅ {mark.mark}⃣ {mark.text}")

        elif new_count < old_count:  # old mark
            changed_marks.setdefault(mark.date, {})
            changed_marks[mark.date].setdefault(mark.lesson, [])
            for _ in range(old_count - new_count):
                changed_marks[mark.date][mark.lesson].append(f"❌ {mark.mark}⃣ {mark.text}")

    if changed_marks:
        if await child.child_count():
            api: DiaryApi = (await bp.state_dispenser.get(child.vk_id)).payload["api"]
            name = api.user.children[child.child_id].name
            message = f"🔔 Изменения в оценках\n🧒{name}\n\n"
        else:
            message = "🔔 Изменения в оценках\n\n"
        for date, lesson_marks in sorted(changed_marks.items()):
            message += "📅 " + date + "\n"
            for lesson, information in sorted(lesson_marks.items()):
                message += "📚 " + lesson + "\n"
                for text in information:
                    message += text + "\n"
            message += "\n"
        await bp.api.messages.send(child.vk_id, message=message, random_id=0)
        DATA[child] = new_marks, new_period


# every 5 minute
@scheduler.scheduled_job("cron", id="marks_job", minute="*/5", timezone="europe/moscow")
async def default_scheduler():
    logger.debug("Check new marks")
    for child in (await session.execute(childs_marks)).scalars():
        await marks_job(child)


async def start():
    children_count = 0

    child: Child
    for child in (
        await session.execute(select(Child).where(Child.marks_notify.is_(True)))
    ).scalars():
        children_count += 1
        DATA[child] = await Marks.from_api(child)

    await admin_log("Уведомления запущены.\n" f"🔸 Уведомления: {children_count}")
    scheduler.start()


async def add(child: Child):
    DATA.setdefault(child, await Marks.from_api(child))


async def delete(child: Child):
    DATA.pop(child, None)


def stop():
    scheduler.shutdown()
