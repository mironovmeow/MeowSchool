"""
Schedulers module (marks notification)
"""
import datetime
from typing import Dict, List, Optional, Tuple

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from vkbottle.bot import Blueprint
from vkbottle.modules import logger

from bot.db import User
from diary import DiaryApi, LessonsScoreObject


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
    def from_api(cls, lessons_score: LessonsScoreObject) -> Dict["Marks", int]:
        ans = {}
        for lesson, data in lessons_score.data.items():
            for score in data:
                for text, marks_list in score.marks.items():
                    for mark_int in marks_list:
                        marks = cls(lesson, score.date, text, mark_int)
                        ans.setdefault(marks, 0)
                        ans[marks] += 1
        return ans

    def __hash__(self):
        return hash((self.lesson, self.date, self.text, self.mark))

    def __eq__(self, other):
        if isinstance(other, Marks):
            return self.lesson == other.lesson and \
                   self.date == other.date and \
                   self.text == other.text and \
                   self.mark == other.mark
        return False


scheduler = AsyncIOScheduler()
bp = Blueprint(name="Scheduler")  # use for message_send

DATA: Dict[Tuple[User, int], Dict[Marks, int]] = {}  # todo load from database


def _today() -> str:
    return datetime.date.today().strftime("%d.%m.%Y")


@scheduler.scheduled_job("cron", id="marks_job", minute="*/5", house="7-23", timezone="asia/krasnoyarsk")
async def marks_job():
    logger.debug("Check new marks")

    for user, old_marks in DATA.items():
        new_marks = Marks.from_api(await get_marks(*user))

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
            message = "🔔 Изменения в оценках\n\n"
            for date, lesson_marks in sorted(changed_marks.items()):
                message += "📅 " + date + "\n"
                for lesson, information in sorted(lesson_marks.items()):
                    message += "📚 " + lesson + "\n"
                    for text in information:
                        message += text + "\n"
                message += "\n"
            await bp.api.messages.send(user[0].vk_id, message=message, random_id=0)
            DATA[user] = new_marks


async def get_marks(user: User, child_index: int) -> Optional[LessonsScoreObject]:
    state_peer = await bp.state_dispenser.get(user.vk_id)
    if state_peer:
        api: DiaryApi = state_peer.payload["api"]
        return await api.lessons_scores(_today(), child=child_index)
    return None


async def start():
    user = await User.get(248525108)
    DATA[(user, 0)] = Marks.from_api(await get_marks(user, 0))
    scheduler.start()


def stop():
    scheduler.shutdown()
