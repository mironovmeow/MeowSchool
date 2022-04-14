"""
Database module (sqlalchemy with aiosqlite)
"""
import asyncio
from typing import List, Optional

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, func, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Mapped, declarative_base, relationship

Base = declarative_base()
engine = create_async_engine("sqlite+aiosqlite:///db.sqlite3", future=True)
session = AsyncSession(engine, expire_on_commit=False)


class User(Base):
    __tablename__ = "users"

    vk_id = Column(Integer, primary_key=True)
    diary_session = Column(String, nullable=False)
    diary_information = Column(String, nullable=False)

    children: Mapped["Child"] = relationship("Child", lazy="selectin", cascade="all")
    chats: Mapped["Chat"] = relationship("Chat", lazy="selectin", cascade="all")

    @classmethod
    async def create(cls, vk_id, diary_session, diary_information, children, chats) -> "User":
        user = cls(
            vk_id=vk_id,
            diary_session=diary_session,
            diary_information=diary_information,
            children=children,
            chats=chats,
        )
        session.add(user)
        await session.commit()
        return user

    @classmethod
    async def get(cls, vk_id) -> Optional["User"]:
        return await session.get(cls, vk_id)

    @classmethod
    async def get_all(cls) -> List["User"]:
        return (await session.execute(select(cls))).scalars().all()

    @staticmethod
    async def save():
        await session.commit()

    async def delete(self):
        await session.delete(self)
        await session.commit()

    @staticmethod
    async def count() -> int:
        return (await session.execute(select(func.count(User.vk_id)))).scalar_one()

    def __repr__(self):
        return f'User(vk_id={self.vk_id!r}, diary_session="...", diary_information="...")'

    __mapper_args__ = {"eager_defaults": True}


class Child(Base):
    __tablename__ = "child"

    vk_id = Column(Integer, ForeignKey("users.vk_id"), primary_key=True, nullable=False)
    child_id = Column(Integer, primary_key=True, nullable=False)
    marks_notify = Column(Boolean, default=False, nullable=False)

    @staticmethod
    async def update_count(vk_id: int, child_count: int):
        r: List[Child] = (
            (await session.execute(select(Child).where(Child.vk_id.is_(vk_id)))).scalars().all()
        )
        for i in range(len(r), child_count, -1):
            await session.delete(r[i])
        for i in range(len(r), child_count):
            session.add(Child(vk_id=vk_id, child_id=i))
        await session.commit()

    @staticmethod
    async def save():
        await session.commit()

    @staticmethod
    async def marks_count() -> int:
        return (
            await session.execute(
                select(func.count(Child.vk_id)).where(Child.marks_notify.is_(True))
            )
        ).scalar_one()

    async def child_count(self) -> int:
        return (
            await session.execute(
                select(func.count(Child.child_id)).where(Child.vk_id == self.vk_id)
            )
        ).scalar_one()

    def __repr__(self):
        return f"Child(vk_id={self.vk_id!r}, child_id={self.child_id!r}, marks_notify=False)"


class Chat(Base):
    __tablename__ = "chats"

    peer_id = Column(Integer, primary_key=True)
    vk_id = Column(Integer, ForeignKey("users.vk_id"), nullable=False)

    @classmethod
    async def get(cls, peer_id) -> Optional["Chat"]:
        return await session.get(cls, peer_id)

    @classmethod
    async def create(cls, peer_id, vk_id) -> "Chat":
        chat = cls(
            peer_id=peer_id,
            vk_id=vk_id,
        )
        session.add(chat)
        await session.commit()
        return chat

    async def delete(self):
        await session.delete(self)
        await session.commit()

    @staticmethod
    async def count() -> int:
        return (await session.execute(select(func.count(Chat.vk_id)))).scalar_one()

    def __repr__(self):
        return f"Chat(peer_id={self.peer_id!r}, vk_id=0)"


async def start_up():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await session.begin()


async def close():
    await session.close()


if __name__ == "__main__":
    asyncio.run(Child.update_count(248525108, 2))
