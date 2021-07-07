import typing
from asyncio import get_event_loop

from aiohttp import ClientSession

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
            }
        )
        async with session.get(
            f'https://sosh.mon-ra.ru/rest/login?'
            f'login={login}&password={password}'
        ) as r:
            try:
                pupil = diary_types.LoginObject.reformat(await r.json())
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
            return diary_types.DiaryObject.reformat(await r.json())

    async def progress_average(self, date: str):
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/progress_average',
                data={
                    "pupil_id": self.pupil.children[0].id,
                    "date": date
                }
        ) as r:
            return diary_types.ProgressAverageObject.parse_obj(await r.json())

    async def additional_materials(self, lesson_id: int):
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/additional_materials',
                data={
                    "pupil_id": self.pupil.children[0].id,
                    "lesson_id": lesson_id
                }
        ) as r:
            return diary_types.AdditionalMaterialsObject.parse_obj(await r.json())

    async def school_meetings(self):
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/school_meetings',
                data={
                    "pupil_id": self.pupil.children[0].id
                }
        ) as r:
            return diary_types.SchoolMeetingsObject.parse_obj(await r.json())

    async def totals(self, date: str):
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/totals',
                data={
                    "pupil_id": self.pupil.children[0].id,
                    "date": date
                }
        ) as r:
            return diary_types.TotalsObject.parse_obj(await r.json())

    async def check_food(self):
        async with self._session.post(
                'https://sosh.mon-ra.ru//rest/check_food'
        ) as r:
            # {
            # 	"food_plugin": "NO"
            # }
            return diary_types.CheckFoodObject.parse_obj(await r.json())

    async def lessons_scores(self, date: str, subject: str):
        async with self._session.post(
                'https://sosh.mon-ra.ru//rest/lessons_scores',
                data={
                    "pupil_id": self.pupil.children[0].id,
                    "date": date,
                    "subject": subject
                }
        ) as r:
            return diary_types.LessonsScoreObject.parse_obj(await r.json())

    async def logout(self):
        async with self._session.post(
                'https://sosh.mon-ra.ru/rest/logout',
        ) as r:
            return diary_types.BaseResponse.parse_obj(await r.json())

    @staticmethod
    def run(func: typing.Callable[[], typing.Coroutine]) -> None:
        try:
            lp = get_event_loop()
            lp.run_until_complete(func())
        except Exception as e:
            print(e.__class__.__name__, e)
