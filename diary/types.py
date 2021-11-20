import datetime
from typing import Dict, List, Optional, Sequence, Type, TypeVar, Union

from aiohttp import ClientResponse, ClientSession
from pydantic import validator
from pydantic.fields import Field
from pydantic.main import BaseModel

ObjectType = TypeVar("ObjectType", bound="BaseResponse")


class APIError(BaseException):
    def __init__(
            self,
            resp: ClientResponse,
            session: ClientSession,
    ):
        self.resp = resp
        self.session = session

    def __str__(self):
        return f"APIError [{self.resp.status}]"

    async def json_success(self) -> bool:
        json = await self.resp.json()
        return json.get("success", False)


class BaseResponse(BaseModel):
    success: bool  # checking in /diary/api.py

    @classmethod
    def reformat(cls: Type[ObjectType], obj: dict) -> ObjectType:
        return cls.parse_obj(obj)


# /rest/login

class ChildObject(BaseModel):
    id: int
    name: str
    school: str


class LoginObject(BaseResponse):
    children: List[ChildObject]
    profile_id: int
    id: int
    type: str
    fio: str

    @classmethod
    def reformat(cls: Type[ObjectType], obj: dict) -> ObjectType:
        return cls.parse_obj({
            'success': obj.get("success"),
            'children': [
                {
                    "id": child[0],
                    "name": child[1],
                    "school": child[2]
                } for child in obj.get("childs", [])  # stupid api
            ],
            'profile_id': obj.get("profile_id"),
            'id': obj.get("id"),
            'type': obj.get("type"),
            'fio': obj.get("fio")
        })


# /rest/diary

def _mark(marks: List[list]) -> str:  # for DiaryLessonObject.info()
    if len(marks) == 0:  # no marks
        return ""
    marks_str = ""
    for mark_list in marks[0][len(marks[0]) // 2:]:
        for mark_str in mark_list:
            if mark_str:
                marks_str += mark_str + "️⃣"  # use combinations of emoji
    return marks_str


class DiaryLessonObject(BaseModel):  # TODO
    comment: str
    discipline: str
    remark: str  # what it?  now it's ''
    attendance: Union[list, str]  # what it?  now it's ['', 'Был']
    room: str
    next_homework: Sequence[Union[str, None]]  # first: str or none, second: ''
    individual_homework: list = Field(alias="individualhomework")  # for beautiful use in code, now it []
    marks: List[list]  # [list for marks name, list of marks]  API IS SO STUPID!!!
    date_str: str = Field(alias="date")  # 21.12.2012
    lesson: list  # [id, str, start_time_str, end_time_str]
    homework: List[str]
    teacher: str
    next_individual_homework: list = Field(alias="next_individualhomework")  # check structure
    subject: str

    @property
    def date(self) -> datetime.date:
        return datetime.date(*map(int, self.date_str.split(".")[::-1]))

    def info(self, is_chat: bool) -> str:
        if is_chat:
            return f"{self.lesson[1]}: {self.discipline} {_mark(self.marks)}\n" + \
                   "\n".join(self.homework)
        return f"{self.lesson[1]}: {self.discipline}\n" + "\n".join(self.homework)


_day_of_week: List[str] = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]


class DiaryDayObject(BaseModel):
    kind: Optional[str]
    date_str: str = Field(alias="date")  # 21.12.2012
    lessons: Optional[List[DiaryLessonObject]]

    @property
    def date(self) -> datetime.date:
        return datetime.date(*map(int, self.date_str.split(".")[::-1]))

    def info(self, is_chat: bool) -> str:
        text = f"{_day_of_week[self.date.weekday()]} [{self.date_str}]\n"
        if self.lessons:
            text += "\n\n".join(lesson.info(is_chat) for lesson in self.lessons)
        else:
            text += self.kind
        return text


class DiaryObject(BaseResponse):
    days: List[DiaryDayObject]

    @classmethod
    def reformat(cls: Type[ObjectType], obj: dict) -> ObjectType:
        data = {"success": obj.get("success", False), "days": []}
        for value_day in obj.get("days", []):
            day = {
                "date": value_day[0],
                "lessons": value_day[1].get("lessons"),
                "kind": value_day[1].get("kind")
            }
            data["days"].append(day)
        return cls.parse_obj(data)

    def info(self, is_chat: bool = False):
        return "РАСПИСАНИЕ УРОКОВ\n\n" + "\n\n".join(day.info(is_chat) for day in self.days)


# /rest/progress_average

def _check_value_of_mark(value: str) -> Union[bool, float]:  # for ProgressDataObject
    if not 1.00 <= float(value) <= 5.00:
        return False
    return float(value)


def _bar(mark: float, full: bool) -> str:  # for ProgressDataObject
    if full:
        if mark < 1.5:
            return "🟫⬜⬜⬜⬜"
        elif mark < 2.5:
            return "🟥🟥⬜⬜⬜"
        elif mark < 3.5:
            return "🟧🟧🟧⬜⬜"
        elif mark < 4.5:
            return "🟨🟨🟨🟨⬜"
        else:
            return "🟩🟩🟩🟩🟩"
    else:
        if mark < 1.5:
            return "🟫"
        elif mark < 2.5:
            return "🟥"
        elif mark < 3.5:
            return "🟧"
        elif mark < 4.5:
            return "🟨"
        else:
            return "🟩"


class ProgressDataObject(BaseModel):
    total: Optional[float]
    data: Optional[Dict[str, float]]  # discipline: mark

    @classmethod  # fix pycharm warning
    @validator("total")
    def check_total(cls, value):
        return _check_value_of_mark(value)

    @classmethod  # fix pycharm warning
    @validator("data", each_item=True)
    def check_data(cls, value):
        return _check_value_of_mark(value)

    def info(self, full: bool) -> str:
        if full:
            return "\n".join(f"{_bar(mark, True)} ({mark:.2f}): {subject}"
                             for subject, mark in sorted(self.data.items(), key=lambda v: (-v[1], v[0])))
        else:
            return "\n".join(f"{_bar(mark, False)} {subject}"
                             for subject, mark in sorted(self.data.items(), key=lambda v: (-v[1], v[0])))


class ProgressAverageObject(BaseResponse):
    kind: Optional[str]
    self: ProgressDataObject
    class_year: ProgressDataObject = Field(alias="classyear")
    level: ProgressDataObject
    sub_period: str = Field(alias="subperiod")

    def info(self, full: bool = False) -> str:
        if self.kind:
            return self.kind
        return f"{self.sub_period}\n\n{self.self.info(full)}"


# /rest/additional_materials

class AdditionalMaterialsObject(BaseResponse):
    kind: Optional[str]  # 26.04.2021  todo


# /rest/school_meetings

class SchoolMeetingsObject(BaseResponse):  # please, contact with me if in your school work this function
    kind: Optional[str]


# /rest/totals

class TotalsObject(BaseResponse):  # todo how to do it
    period: str
    period_types: List[str]  # ['1 Полугодие', '2 Полугодие', 'Годовая']
    subjects: Dict[str, List[str]]  # 'Русский язык': ['4', '0', '0']
    period_begin: str
    period_end: str


# /lessons_scores

class ScoreObject(BaseModel):  # remake
    date: str  # 2012-21-12
    marks: Dict[str, List[str]]  # text: [marks (str)]


def get_score_stat(scores: List[ScoreObject]) -> str:
    stats = {"5": 0, "4": 0, "3": 0, "2": 0, "1": 0}
    for score in scores:
        for marks in score.marks.values():
            for mark in marks:
                stats[mark] += 1

    return "  ".join(f"{mark}⃣: {count}" for mark, count in stats.items())


class LessonsScoreObject(BaseResponse):
    kind: Optional[str]
    sub_period: Optional[str] = Field(alias="subperiod")
    data: Optional[Dict[str, List[ScoreObject]]]  # lesson: ScoreObject

    def info(self):
        if self.data is None or len(self.data) == 0:
            return self.kind
        return "\n".join(f"{lesson}:\n{get_score_stat(score)}" for lesson, score in self.data.items())


# /check_food

class CheckFoodObject(BaseModel):  # please, contact with me if in your school work this function
    food_plugin: str  # "NO" and maybe "YES"


__all__ = (
    "APIError",
    "LoginObject",
    "DiaryObject",
    "ProgressAverageObject",
    "AdditionalMaterialsObject",
    "SchoolMeetingsObject",
    "TotalsObject",
    "LessonsScoreObject",
    "CheckFoodObject"
)
