import typing

from aiohttp import ClientSession, TCPConnector, ClientResponse
from loguru import logger

from diary import types


async def _check_response(r: ClientResponse) -> str:
    if not r.ok:
        logger.info(f"Request failed {r.status}")
        raise types.APIError(r)

    json = await r.json()
    if json.get("success") is False:
        logger.info(f"Request failed {json}")
        raise types.APIError(r, json_success=False)

    logger.debug(f"Request returned {json}")
    return json


class DiaryApi:
    def __init__(self, session: ClientSession, user: types.LoginObject, diary_session: str):
        self._session = session
        self.user = user
        self.diary_session = diary_session

    def __str__(self) -> str:
        return f'<DiaryApi> {self.user.fio}'

    @property
    def closed(self) -> bool:
        return self._session.closed

    async def close(self) -> None:
        await self._session.close()

    @classmethod
    async def auth_by_diary_session(cls, diary_session: str) -> "DiaryApi":
        session = ClientSession(
            headers={
                "User-Agent": "MeowApi/1 (vk.com/meow_py)",
                "Connection": "keep-alive"
            },
            connector=TCPConnector(ssl=False),
            cookies={"sessionid": diary_session}
        )
        async with session.get(
                'https://sosh.mon-ra.ru/rest/login'
        ) as r:
            json = await _check_response(r)
            user = types.LoginObject.reformat(json)
            return cls(session, user, diary_session)

    @classmethod
    async def auth_by_login(cls, login: str, password: str) -> "DiaryApi":
        session = ClientSession(
            headers={"User-Agent": "MeowApi/1 (vk.com/meow_py)"},
            connector=TCPConnector(ssl=False)
        )
        async with session.get(
                f'https://sosh.mon-ra.ru/rest/login?'
                f'login={login}&password={password}'
        ) as r:
            json = await _check_response(r)

            diary_cookie = r.cookies.get("sessionid")

            user = types.LoginObject.reformat(json)
            diary = cls(session, user, diary_cookie.value)
            return diary

    async def diary(self, from_date: str, to_date: typing.Union[str, None] = None):
        if to_date is None:
            to_date = from_date

        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/diary',
                data={
                    "pupil_id": self.user.children[0].id,
                    "from_date": from_date,
                    "to_date": to_date
                }
        ) as r:
            json = await _check_response(r)
            return types.DiaryObject.reformat(json)

    async def progress_average(self, date: str):
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/progress_average',
                data={
                    "pupil_id": self.user.children[0].id,
                    "date": date
                }
        ) as r:
            json = await _check_response(r)
            return types.ProgressAverageObject.parse_obj(json)

    async def additional_materials(self, lesson_id: int):
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/additional_materials',
                data={
                    "pupil_id": self.user.children[0].id,
                    "lesson_id": lesson_id
                }
        ) as r:
            json = await _check_response(r)
            return types.AdditionalMaterialsObject.parse_obj(json)

    async def school_meetings(self):
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/school_meetings',
                data={
                    "pupil_id": self.user.children[0].id
                }
        ) as r:
            json = await _check_response(r)
            return types.SchoolMeetingsObject.parse_obj(json)

    async def totals(self, date: str):
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/totals',
                data={
                    "pupil_id": self.user.children[0].id,
                    "date": date
                }
        ) as r:
            json = await _check_response(r)
            return types.TotalsObject.parse_obj(json)

    async def lessons_scores(self, date: str, subject: str):
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/lessons_scores',
                data={
                    "pupil_id": self.user.children[0].id,
                    "date": date,
                    "subject": subject
                }
        ) as r:
            json = await _check_response(r)
            return types.LessonsScoreObject.parse_obj(json)

    async def check_food(self):
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/check_food'
        ) as r:
            json = await _check_response(r)
            return types.CheckFoodObject.parse_obj(json)

    async def logout(self):
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/logout',
        ) as r:
            json = await _check_response(r)
            return types.BaseResponse.parse_obj(json)
