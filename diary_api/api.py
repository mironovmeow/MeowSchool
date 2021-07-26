import typing

from aiohttp import ClientSession, TCPConnector
from loguru import logger

from . import diary_types


class DiaryApi:
    def __init__(self, session: ClientSession, user: diary_types.LoginObject, diary_session: str):
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
        async with ClientSession(
                headers={"User-Agent": "MeowApi/1 (vk.com/meow_py)"},
                connector=TCPConnector(ssl=False),
                cookies={"sessionid": diary_session}
        ) as session:
            async with session.get(
                    'https://sosh.mon-ra.ru/rest/login'
            ) as r:
                if not r.ok:
                    logger.warning(f"Request failed")
                    pass

                json = await r.json()
                if json["success"] is False:
                    logger.warning(f"Request failed {json}")
                    pass

                logger.debug(f"Request returned {json}")
                user = diary_types.LoginObject.reformat(json)
                return cls(session, user, diary_session)

    @classmethod
    async def auth_by_login(cls, login: str, password: str) -> "DiaryApi":
        async with ClientSession(
                headers={"User-Agent": "MeowApi/1 (vk.com/meow_py)"},
                connector=TCPConnector(ssl=False)
        ) as session:
            async with session.get(
                    f'https://sosh.mon-ra.ru/rest/login?'
                    f'login={login}&password={password}'
            ) as r:
                if not r.ok:
                    pass

                json = await r.json()
                if json["success"] is False:
                    logger.warning(f"Request failed {json}")
                    pass

                diary_cookie = r.cookies.get("sessionid")
                if not diary_cookie:
                    logger.warning(f"Diary session is undefined")
                    pass

                logger.debug(f"Request returned {json}")
                user = diary_types.LoginObject.reformat(json)
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
            if not r.ok:
                logger.warning(f"Request failed")
                pass

            json = await r.json()
            if json["success"] is False:
                logger.warning(f"Request failed {json}")
                pass

            logger.debug(f"Request returned {json}")
            return diary_types.DiaryObject.reformat(json)

    async def progress_average(self, date: str):
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/progress_average',
                data={
                    "pupil_id": self.user.children[0].id,
                    "date": date
                }
        ) as r:
            if not r.ok:
                logger.warning(f"Request failed")
                pass

            json = await r.json()
            if json["success"] is False:
                logger.warning(f"Request failed {json}")
                pass

            logger.debug(f"Request returned {json}")
            return diary_types.ProgressAverageObject.parse_obj(json)

    async def additional_materials(self, lesson_id: int):
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/additional_materials',
                data={
                    "pupil_id": self.user.children[0].id,
                    "lesson_id": lesson_id
                }
        ) as r:
            if not r.ok:
                logger.warning(f"Request failed")
                pass

            json = await r.json()
            if json["success"] is False:
                logger.warning(f"Request failed {json}")
                pass

            logger.debug(f"Request returned {json}")
            return diary_types.AdditionalMaterialsObject.parse_obj(json)

    async def school_meetings(self):
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/school_meetings',
                data={
                    "pupil_id": self.user.children[0].id
                }
        ) as r:
            if not r.ok:
                logger.warning(f"Request failed")
                pass

            json = await r.json()
            if json["success"] is False:
                logger.warning(f"Request failed {json}")
                pass

            logger.debug(f"Request returned {json}")
            return diary_types.SchoolMeetingsObject.parse_obj(json)

    async def totals(self, date: str):
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/totals',
                data={
                    "pupil_id": self.user.children[0].id,
                    "date": date
                }
        ) as r:
            if not r.ok:
                logger.warning(f"Request failed")
                pass

            json = await r.json()
            if json["success"] is False:
                logger.warning(f"Request failed {json}")
                pass

            logger.debug(f"Request returned {json}")
            return diary_types.TotalsObject.parse_obj(json)

    async def lessons_scores(self, date: str, subject: str):
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/lessons_scores',
                data={
                    "pupil_id": self.user.children[0].id,
                    "date": date,
                    "subject": subject
                }
        ) as r:
            if not r.ok:
                logger.warning(f"Request failed")
                pass

            json = await r.json()
            if json["success"] is False:
                logger.warning(f"Request failed {json}")
                pass

            logger.debug(f"Request returned {json}")
            return diary_types.LessonsScoreObject.parse_obj(json)

    async def check_food(self):
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/check_food'
        ) as r:
            if not r.ok:
                logger.warning(f"Request failed")
                pass

            json = await r.json()
            if json["success"] is False:
                logger.warning(f"Request failed {json}")
                pass

            logger.debug(f"Request returned {json}")
            return diary_types.CheckFoodObject.parse_obj(json)

    async def logout(self):
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/logout',
        ) as r:
            if not r.ok:
                logger.warning(f"Request failed")
                pass

            json = await r.json()
            if json["success"] is False:
                logger.warning(f"Request failed {json}")
                pass

            logger.debug(f"Request returned {json}")
            return diary_types.BaseResponse.parse_obj(json)
