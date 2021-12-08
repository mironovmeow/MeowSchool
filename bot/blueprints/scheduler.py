"""
Schedulers module (marks notification)
"""
import datetime
from typing import Dict, List, Optional, Tuple

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from vkbottle.bot import Blueprint
from vkbottle.modules import logger

from bot.blueprints.other import admin_log
from bot.db import Child, select, session
from bot.error_handler import scheduler_error_handler
from diary import DiaryApi


class Marks:
    def __init__(
            self,
            lesson: str,
            date: str,
            text: str,
            mark: str
    ):
        self.lesson = lesson
        self.date = date
        self.text = text
        self.mark = mark

    @classmethod
    async def from_api(cls, child: Child) -> Tuple[Dict["Marks", int], Optional[str]]:
        state_peer = await bp.state_dispenser.get(child.vk_id)
        if state_peer:  # todo обработка удаления state_peer
            api: DiaryApi = state_peer.payload["api"]
            lessons_score = await api.lessons_scores(_today(), child=child.child_id)
            ans = {}
            for lesson, data in lessons_score.data.items():
                for score in data:
                    for text, marks_list in score.marks.items():
                        for mark_int in marks_list:
                            marks = cls(lesson, score.date, text, mark_int)
                            ans.setdefault(marks, 0)
                            ans[marks] += 1
            return ans, lessons_score.sub_period
        return {}, None

    def __hash__(self):
        return hash((self.lesson, self.date, self.text, self.mark))

    def __eq__(self, other):
        if isinstance(other, Marks):
            return self.lesson == other.lesson and \
                   self.date == other.date and \
                   self.text == other.text and \
                   self.mark == other.mark
        return False


default_stmt = select(Child).where(Child.marks == 1)
donut_stmt = select(Child).where(Child.marks == 2)
vip_stmt = select(Child).where(Child.marks == 3)
admin_stmt = select(Child).where(Child.marks == 4)

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
        await bp.api.messages.send(child.vk_id, message=f"🔔 Изменение периода: {new_period}", random_id=0)
        old_marks = {}

    changed_marks: Dict[str, Dict[str, List[str]]] = {}  # date: {lesson: [information]}

    mark_keys = old_marks.keys() | new_marks.keys()

    for mark in mark_keys:
        old_count = old_marks.get(mark, 0)
        new_count = new_marks.get(mark, 0)

        if new_count > old_count:  # new mark
            changed_marks.setdefault(mark.date, {})
            changed_marks[mark.date].setdefault(mark.lesson, [])
            for _ in range(new_count - old_count):
                changed_marks[mark.date][mark.lesson].append(
                    f"✅ {mark.mark}⃣ {mark.text}"
                )

        elif new_count < old_count:  # old mark
            changed_marks.setdefault(mark.date, {})
            changed_marks[mark.date].setdefault(mark.lesson, [])
            for _ in range(old_count - new_count):
                changed_marks[mark.date][mark.lesson].append(
                    f"❌ {mark.mark}⃣ {mark.text}"
                )

    if changed_marks:
        if len(child.user.children) > 1:
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


# every 2 hours
@scheduler.scheduled_job("cron", id="marks_default_job", hour="7-23/2", timezone="asia/krasnoyarsk")
async def default_scheduler():
    logger.debug("Check default new marks")
    for child in (await session.execute(default_stmt)).scalars():
        await marks_job(child)


# every 15 minutes
@scheduler.scheduled_job("cron", id="marks_donut_job", minute="*/15", hour="7-23", timezone="asia/krasnoyarsk")
async def donut_scheduler():
    logger.debug("Check donut new marks")
    for child in (await session.execute(donut_stmt)).scalars():
        await marks_job(child)


# every 5 minutes
@scheduler.scheduled_job("cron", id="marks_vip_job", minute="*/5", hour="7-23", timezone="asia/krasnoyarsk")
async def vip_scheduler():
    logger.debug("Check vip new marks")
    for child in (await session.execute(vip_stmt)).scalars():
        await marks_job(child)


# every 2 minutes
@scheduler.scheduled_job("cron", id="marks_admin_job", minute="*/2", hour="7-23", timezone="asia/krasnoyarsk")
async def admin_scheduler():
    logger.debug("Check admin new marks")
    for child in (await session.execute(admin_stmt)).scalars():
        await marks_job(child)


async def start():
    child_count = 0

    child: Child
    for child in (await session.execute(select(Child).where(Child.marks > 0))).scalars():
        child_count += 1
        DATA[child] = await Marks.from_api(child)

    await admin_log(
        "Уведомления запущены.\n"
        f"🔸 Уведомления: {child_count}"
    )
    scheduler.start()


async def add(child: Child):
    DATA.setdefault(child, await Marks.from_api(child))


async def delete(child: Child):
    DATA.pop(child, None)


def stop():
    scheduler.shutdown()
