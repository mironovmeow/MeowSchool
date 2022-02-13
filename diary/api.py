"""
Api module (on aiohttp)
"""
from typing import Optional, Type

from aiohttp import ClientResponse, ClientSession, ClientTimeout, ContentTypeError, TCPConnector

from . import types

try:
    from loguru import logger
except ImportError:
    from logging import Logger
    logger = Logger("diary")


async def _check_response(r: ClientResponse, session: ClientSession) -> dict:
    if not r.ok:
        logger.info(f"Request failed. Bad status: {r.status}")
        raise types.APIError(r, session)

    try:
        json = await r.json()
        logger.debug(f"Response with {json}")

        if json.get("error") is not None:  # {"error": "Произошла непредвиденная ошибка ..."}
            json["success"] = False
            json["kind"] = json["error"]

        if json.get("success", False) is False:
            logger.info(f"Request failed. Not success.")
            raise types.APIError(r, session, json=json)

        return json

    except ContentTypeError:
        logger.info(f"Request failed. ContentTypeError")
        raise types.APIError(r, session)


class DiaryApi:
    def __init__(self, session: ClientSession, diary_session: str, diary_information: dict):
        self._session = session
        self.diary_information = diary_information
        self.diary_session = diary_session
        self.user = types.LoginObject.reformat(diary_information)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.logout()
        await self.close_session()

    def __str__(self) -> str:
        return f'<DiaryApi {self.user.fio}>'

    @property
    def closed(self) -> bool:
        return self._session.closed

    async def close_session(self) -> None:
        logger.info(f"Closing DiaryApi {self.user.fio}")
        await self._session.close()

    async def _post(self, cls: Type[types.ObjectType], endpoint: str, data: Optional[dict] = None) -> types.ObjectType:
        logger.debug(f"Request \"{endpoint}\" with data {data}")
        async with self._session.post(
                f"https://sosh.mon-ra.ru/rest/{endpoint}",
                data=data
        ) as r:
            json = await _check_response(r, self._session)
            return cls.reformat(json)

    @classmethod
    async def auth_by_diary_session(cls, diary_session: str, diary_information: dict) -> "DiaryApi":
        session = ClientSession(
            headers={
                "User-Agent": "MeowApi/3 (vk.com/schoolbot04)",
                "Connection": "keep-alive"
            },
            connector=TCPConnector(ssl=False),  # it's bad, i know
            cookies={"sessionid": diary_session},
            timeout=ClientTimeout(10)
        )
        return cls(session, diary_session, diary_information)

    @classmethod
    async def auth_by_login(cls, login: str, password: str) -> "DiaryApi":
        logger.debug("Request \"login\" with data {\"login\": ..., \"password\": ...}")
        session = ClientSession(
            headers={"User-Agent": "MeowApi/3 (vk.com/schoolbot04)"},
            connector=TCPConnector(ssl=False),  # it's bad, i know
            timeout=ClientTimeout(10)
        )
        async with session.get(
                f'https://sosh.mon-ra.ru/rest/login?'
                f'login={login}&password={password}'

        ) as r:
            json = await _check_response(r, session)
            diary_cookie = r.cookies.get("sessionid")

            return cls(session, diary_cookie.value, json)

    async def diary(self, from_date: str, to_date: Optional[str] = None, *, child: int = 0) -> types.DiaryObject:
        if to_date is None:
            to_date = from_date

        return await self._post(types.DiaryObject, "diary", {
            "pupil_id": self.user.children[child].id,
            "from_date": from_date,
            "to_date": to_date
        })

    async def progress_average(self, date: str, *, child: int = 0) -> types.ProgressAverageObject:
        return await self._post(types.ProgressAverageObject, "progress_average", {
            "pupil_id": self.user.children[child].id,
            "date": date
        })

    async def additional_materials(self, lesson_id: int, *, child: int = 0) -> types.AdditionalMaterialsObject:
        return await self._post(types.AdditionalMaterialsObject, "additional_materials", {
            "pupil_id": self.user.children[child].id,
            "lesson_id": lesson_id
        })

    async def school_meetings(self, *, child: int = 0) -> types.SchoolMeetingsObject:
        return await self._post(types.SchoolMeetingsObject, "school_meetings", {
            "pupil_id": self.user.children[child].id
        })

    async def totals(self, date: str, *, child: int = 0) -> types.TotalsObject:
        return await self._post(types.TotalsObject, "totals", {
            "pupil_id": self.user.children[child].id,
            "date": date
        })

    async def lessons_scores(
            self,
            date: str,
            subject: Optional[str] = None,
            *,
            child: int = 0
    ) -> types.LessonsScoreObject:
        if subject is None:
            subject = ""

        return await self._post(types.LessonsScoreObject, "lessons_scores", {
            "pupil_id": self.user.children[child].id,
            "date": date,
            "subject": subject
        })

    async def logout(self) -> types.BaseResponse:
        return await self._post(types.BaseResponse, "logout")

    async def check_food(self) -> types.CheckFoodObject:
        logger.debug("Request \"check_food\" with data None")
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/check_food'
        ) as r:
            json = await _check_response(r, self._session)
            return types.CheckFoodObject.parse_obj(json)
