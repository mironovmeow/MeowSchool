import typing

from aiohttp import ClientSession, TCPConnector
from loguru import logger

from . import diary_types


class DiaryApi:
    def __init__(self, session: ClientSession, pupil: diary_types.LoginObject) -> None:
        cookies = list(session.cookie_jar)
        if len(cookies) == 1 and cookies[0].key == "sessionid":
            self._session_id = cookies[0].value
            self._session = session
            self.pupil = pupil
            self.error_handler = lambda diary: diary.close()
        else:
            raise diary_types.ApiError("Session is invalid")

    def __str__(self):
        return f'<DiaryApi> {self.pupil.fio}'

    @property
    def closed(self) -> bool:
        return self._session.closed

    @classmethod
    async def auth(cls, login: str, password: str) -> "DiaryApi":
        session = ClientSession(
            headers={
                "User-Agent": "MeowApi/1 (vk.com/meow_py)"
            }, connector=TCPConnector(ssl=False)
        )
        async with session.get(
            f'https://sosh.mon-ra.ru/rest/login?'
            f'login={login}&password={password}'
        ) as r:
            json = await r.json()
            logger.debug(f"Request returned {json}")
            try:
                pupil = diary_types.LoginObject.reformat(json)
            except diary_types.ApiError as error:
                error.response = await r.text()
                await session.close()
                raise error
        return cls(session, pupil)

    async def close(self) -> None:
        await self._session.close()

    async def diary(self, from_date: str, to_date: typing.Union[str, None] = None):
        if to_date is None:
            to_date = from_date

        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/diary',
                data={
                    "pupil_id": self.pupil.children[0].id,
                    "from_date": from_date,
                    "to_date": to_date
                }
        ) as r:
            json = await r.json()
            logger.debug(f"Request returned {json}")
            return diary_types.DiaryObject.reformat(json)

    async def progress_average(self, date: str):
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/progress_average',
                data={
                    "pupil_id": self.pupil.children[0].id,
                    "date": date
                }
        ) as r:
            json = await r.json()
            logger.debug(f"Request returned {json}")
            return diary_types.ProgressAverageObject.parse_obj(json)

    async def additional_materials(self, lesson_id: int):
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/additional_materials',
                data={
                    "pupil_id": self.pupil.children[0].id,
                    "lesson_id": lesson_id
                }
        ) as r:
            json = await r.json()
            logger.debug(f"Request returned {json}")
            return diary_types.AdditionalMaterialsObject.parse_obj(json)

    async def school_meetings(self):
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/school_meetings',
                data={
                    "pupil_id": self.pupil.children[0].id
                }
        ) as r:
            json = await r.json()
            logger.debug(f"Request returned {json}")
            return diary_types.SchoolMeetingsObject.parse_obj(json)

    async def totals(self, date: str):
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/totals',
                data={
                    "pupil_id": self.pupil.children[0].id,
                    "date": date
                }
        ) as r:
            json = await r.json()
            logger.debug(f"Request returned {json}")
            return diary_types.TotalsObject.parse_obj(json)

    async def check_food(self):
        async with self._session.post(
                'https://sosh.mon-ra.ru//rest/check_food'
        ) as r:
            json = await r.json()
            logger.debug(f"Request returned {json}")
            return diary_types.CheckFoodObject.parse_obj(json)

    async def lessons_scores(self, date: str, subject: str):
        async with self._session.post(
                'https://sosh.mon-ra.ru//rest/lessons_scores',
                data={
                    "pupil_id": self.pupil.children[0].id,
                    "date": date,
                    "subject": subject
                }
        ) as r:
            json = await r.json()
            logger.debug(f"Request returned {json}")
            return diary_types.LessonsScoreObject.parse_obj(json)

    async def logout(self):
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/logout',
        ) as r:
            json = await r.json()
            logger.debug(f"Request returned {json}")
            return diary_types.BaseResponse.parse_obj(json)
