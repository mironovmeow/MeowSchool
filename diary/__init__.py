"""
DiaryApi Module

>>> from diary import DiaryApi
>>>
>>> user_api = await DiaryApi.auth_by_login("login", "password")
>>> diary = await user_api.diary("12.12.2021")
>>> print(diary.info())
"""
from .api import DiaryApi
from .types import (APIError, AdditionalMaterialsObject, CheckFoodObject, DiaryObject, LessonsScoreObject, LoginObject,
                    ProgressAverageObject, SchoolMeetingsObject, TotalsObject)
