"""
Database module (sqlalchemy with aiosqlite)
"""
from typing import Iterable, List, Optional

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import declarative_base, relationship, selectinload
from vkbottle.modules import logger

Base = declarative_base()
logger.debug("Connect to database")
_engine = create_async_engine("sqlite+aiosqlite:///db.sqlite3", future=True)
session = AsyncSession(bind=_engine, expire_on_commit=False)


class User(Base):
    __tablename__ = 'users'

    vk_id = Column(Integer, primary_key=True, nullable=False)
    diary_session = Column(String(length=32))
    login = Column(String(length=128))
    password = Column(String(length=128))  # maybe to do something with it?

    donut_level = Column(Integer, default=0)

    refry_id = Column(ForeignKey("users.vk_id"))
    refry_user: Optional["User"] = relationship("User", remote_side=[vk_id])
    # referral_users: async func with session.execute(...).scalars().all()

    chats: List["Chat"] = relationship("Chat", back_populates="user", lazy="selectin", cascade="all, delete-orphan")
    children: List["Child"] = relationship("Child", back_populates="user", lazy="selectin", cascade="all, delete-orphan")

    async def referral_users(self) -> List["User"]:
        stmt = select(User).where(User.refry_id == self.vk_id)
        return (await session.execute(stmt)).scalars().all()

    @classmethod
    async def create(
            cls,
            vk_id: int,
            diary_session: Optional[str] = None,
            login: Optional[str] = None,
            password: Optional[str] = None
    ) -> "User":  # todo try to optimize
        user = cls(vk_id=vk_id, diary_session=diary_session, login=login, password=password)
        session.add(user)
        try:
            await session.flush()
            await session.commit()
            return await session.get(User, vk_id)
        except IntegrityError:  # todo?
            user = await session.get(User, vk_id)
            user.diary_session = diary_session
            user.login = login
            user.password = password
            await session.commit()
            return user

    @classmethod
    async def get(cls, vk_id: int, chats: bool = False, children: bool = False) -> Optional["User"]:
        stmt = select(cls).where(User.vk_id == vk_id)
        if chats:
            stmt = stmt.options(selectinload(cls.chats))
        if children:
            stmt = stmt.options(selectinload(cls.children))
        return (await session.execute(stmt)).scalar_one_or_none()

    @classmethod
    async def get_all(cls, chats: bool = False, children: bool = False) -> Iterable["User"]:
        stmt = select(cls)
        if chats:
            stmt = stmt.options(selectinload(cls.chats))
        if children:
            stmt = stmt.options(selectinload(cls.children))
        return (await session.execute(stmt)).scalars()

    async def delete(self):
        await session.delete(self)
        await session.commit()

    @staticmethod
    async def save():
        await session.commit()

    @staticmethod
    async def count() -> int:
        return (await session.execute(select(func.count(User.vk_id)))).scalar_one()

    def __repr__(self):
        return f"<User(vk_id={self.vk_id}, ...)>"


class Child(Base):
    __tablename__ = "child"

    vk_id = Column(Integer, ForeignKey('users.vk_id'), primary_key=True, nullable=False)
    child_id = Column(Integer, primary_key=True, nullable=False)
    marks_notify = Column(Boolean, default=False, nullable=False)

    user: "User" = relationship("User", lazy="selectin", back_populates="children")

    @classmethod
    # warning! no checking user with vk_id!
    async def create(
            cls,
            vk_id: int,
            child_id: int
    ):
        child = cls(vk_id=vk_id, child_id=child_id)
        session.add(child)
        try:
            await session.flush()
            await session.commit()
        except IntegrityError:  # todo?
            child = await session.get(Child, (vk_id, child_id))
        return child

    @staticmethod
    async def save():
        await session.commit()

    @staticmethod
    async def marks_count() -> int:
        return (await session.execute(select(func.count(Child.vk_id)).where(Child.marks > 0))).scalar_one()

    def __repr__(self):
        return f"<Child(vk_id={self.vk_id}, child_id={self.child_id})>"


class Chat(Base):
    __tablename__ = "chats"

    chat_id = Column(Integer, primary_key=True)
    vk_id = Column(Integer, ForeignKey('users.vk_id'))

    user: "User" = relationship("User", lazy="selectin", back_populates="chats")

    @classmethod
    # warning! no checking user with vk_id!
    async def create(
            cls,
            chat_id: int,
            vk_id: int,
    ) -> "Chat":
        chat = cls(chat_id=chat_id, vk_id=vk_id)
        session.add(chat)
        try:
            await session.flush()
            await session.commit()
        except IntegrityError:
            chat = await session.get(Chat, chat_id)
            chat.vk_id = vk_id
            await session.commit()
        return chat

    @classmethod
    async def get(cls, chat_id: int) -> Optional["Chat"]:
        return await session.get(Chat, chat_id)

    async def delete(self):
        await session.delete(self)
        await session.commit()

    @staticmethod
    async def count() -> int:
        return (await session.execute(select(func.count(Chat.vk_id)))).scalar_one()

    def __repr__(self):
        return f"<Chat(chat_id={self.chat_id}, ...)>"


async def start_up():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close():
    logger.debug("Close connection")
    await session.close()
