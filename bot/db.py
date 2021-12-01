"""
Database module (sqlalchemy with aiosqlite)
"""
from typing import Iterable, Optional

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, select
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

    vk_id = Column(Integer, primary_key=True)
    diary_session = Column(String(length=32))
    login = Column(String(length=128))
    password = Column(String(length=128))  # maybe to do something with it?

    chats = relationship("Chat", back_populates="user", cascade="all, delete, delete-orphan")
    notify = relationship("Notification", back_populates="user", cascade="all, delete, delete-orphan")

    @classmethod
    async def create(
            cls,
            vk_id: int,
            diary_session: Optional[str] = None,
            login: Optional[str] = None,
            password: Optional[str] = None
    ) -> "User":
        user = cls(vk_id=vk_id, diary_session=diary_session, login=login, password=password)
        session.add(user)
        try:
            await session.flush()
            await session.commit()
        except IntegrityError:
            return await cls.get(vk_id)
        return user

    @classmethod
    async def get(cls, vk_id: int) -> Optional["User"]:
        return await session.get(User, vk_id)

    @classmethod
    async def get_all(cls, chats: bool = False, notify: bool = False) -> Iterable["User"]:
        stmt = select(cls)
        if chats:
            stmt = stmt.options(selectinload(cls.chats))
        if notify:
            stmt = stmt.options(selectinload(cls.notify))
        return (await session.execute(stmt)).scalars()

    async def delete(self):
        await session.delete(self)
        await session.commit()

    def __repr__(self):
        return f"<User(vk_id={self.vk_id}, ...)>"


class Notification(Base):
    __tablename__ = "notify"

    vk_id = Column(Integer, ForeignKey('users.vk_id'), primary_key=True, nullable=False)
    child_id = Column(Integer, primary_key=True, nullable=False)
    marks = Column(Boolean, nullable=False, default=False)

    user = relationship("User", back_populates="notify")

    @classmethod
    async def create(
            cls,
            vk_id: int,
            child_id: int
    ):
        notify = cls(vk_id=vk_id, child_id=child_id)
        session.add(notify)
        try:
            await session.flush()
            await session.commit()
        except IntegrityError:
            return await cls.get(vk_id)
        return notify

    @classmethod
    async def get_all(cls, user: bool = False) -> Iterable["Notification"]:
        stmt = select(cls)
        if user:
            stmt = stmt.options(selectinload(cls.user))
        return (await session.execute(stmt)).scalars()

    async def delete(self):
        await session.delete(self)
        await session.commit()

    def __repr__(self):
        return f"<Notify(vk_id={self.vk_id}, child_id={self.child_id})>"


class Chat(Base):
    __tablename__ = "chats"

    chat_id = Column(Integer, primary_key=True)
    vk_id = Column(Integer, ForeignKey('users.vk_id'))

    user = relationship("User", back_populates="chats")

    @classmethod
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
            return await cls.get(chat_id)
        return chat

    @classmethod
    async def get(cls, chat_id: int) -> Optional["Chat"]:
        return await session.get(Chat, chat_id)

    @classmethod
    async def get_all(cls, user: bool = False) -> Iterable["Chat"]:
        stmt = select(cls)
        if user:
            stmt = stmt.options(selectinload(cls.user))
        return (await session.execute(stmt)).scalars()

    async def delete(self):
        await session.delete(self)
        await session.commit()

    def __repr__(self):
        return f"<Chat(chat_id={self.chat_id}, ...)>"


async def start_up():
    async with _engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close():
    logger.debug("Close connection")
    await session.close()
