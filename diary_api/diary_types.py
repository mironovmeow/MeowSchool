from typing import Optional, List, Union, Sequence, Dict

from pydantic import validator
from pydantic.fields import Field
from pydantic.main import BaseModel


class ApiError(BaseException):
    pass  # todo: maybe, add something?


class BaseResponse(BaseModel):
    success: bool  # checking in /diary_api/api.py


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
    def reformat(cls, values) -> "LoginObject":
        return cls.parse_obj({
            'success': values.get("success"),
            'children': [
                {
                    "id": child[0],
                    "name": child[1],
                    "school": child[2]
                } for child in values.get("childs", [])  # stupid api
            ],
            'profile_id': values.get("profile_id"),
            'id': values.get("id"),
            'type': values.get("type"),
            'fio': values.get("fio")
        })


# /rest/diary

def _mark(marks: List[list]) -> str:  # for DiaryLessonObject.info()
    if len(marks) == 0:  # no marks
        return ""
    marks_str = ""
    for mark_list in marks[0][len(marks[0]) // 2:]:
        for mark_str in mark_list:
            if not mark_str:
                marks_str += mark_str + "️⃣"  # use combinations of emoji
    return marks_str


class DiaryLessonObject(BaseModel):  # TODO
    comment: str
    discipline: str
    remark: str  # what it?  now is ''
    attendance: Union[list, str]  # what it?  now it ['', 'Был']
    room: str
    next_homework: Sequence[Union[str, None]]  # first: str or none, second: ''
    individual_homework: list = Field(alias="individualhomework")  # for beautiful use in code, now it []
    marks: List[list]  # [list for marks name, list of marks]  API IS SO STUPID!!!
    date: str  # 21.12.2012 todo change to datetime
    lesson: list  # [id, str, start_time_str, end_time_str]
    homework: List[str]
    teacher: str
    next_individual_homework: list = Field(alias="next_individualhomework")  # check structure
    subject: str

    def info(self) -> str:
        return f"{self.lesson[1]}: {self.discipline} {_mark(self.marks)}\n" + \
               "\n".join(self.homework)


class DiaryDayObject(BaseModel):
    kind: Optional[str]
    date: str  # todo add datetime
    lessons: Optional[List[DiaryLessonObject]]

    def info(self) -> str:
        text = f"{self.date}\n"
        if self.lessons:
            text += "\n\n".join(lesson.info() for lesson in self.lessons)
        else:
            text += self.kind
        return text


class DiaryObject(BaseResponse):
    days: List[DiaryDayObject]

    @classmethod
    def reformat(cls, values) -> "DiaryObject":  # todo make it simple?
        data = {"success": values.get("success", False), "days": []}
        for value_day in values.get("days", []):
            day = {
                "date": value_day[0],
                "lessons": value_day[1].get("lessons"),
                "kind": value_day[1].get("kind")
            }
            data["days"].append(day)
        return cls.parse_obj(data)

    def info(self):
        return "\n\n".join(day.info() for day in self.days)


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
        if self.kind is None:
            return f"{self.sub_period}\n\n{self.self.info(full)}"
        else:
            return self.kind


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


class LessonsScoreObject(BaseResponse):
    kind: Optional[str]
    sub_period: str = Field(alias="subperiod")
    data: Dict[str, ScoreObject]  # lesson: ScoreObject


# /check_food

class CheckFoodObject(BaseModel):  # please, contact with me if in your school work this function
    food_plugin: str  # "NO" and maybe "YES"
