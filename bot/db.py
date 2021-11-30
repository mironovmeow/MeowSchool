"""
Database module (aiosqlite)
"""
from typing import List, Optional, Tuple

import aiosqlite  # move to SQLAlchemy
from vkbottle.modules import logger

db = aiosqlite.connect('db.sqlite3')


async def start_up():
    logger.debug("Connect to database")
    await db
    logger.debug("Create tables")
    await db.execute("""CREATE TABLE IF NOT EXISTS users (
    vk_id INT PRIMARY KEY,
    diary_session VARCHAR (32),
    login VARCHAR (128),
    password VARCHAR (128)
)""")
    await db.execute("""CREATE TABLE IF NOT EXISTS chats (
    chat_id INT PRIMARY KEY,
    vk_id INT NOT NULL
)""")
    await db.commit()


async def close():
    await db.close()


async def add_session(vk_id: int, diary_session: str):
    logger.debug(f"Add session of user: @id{vk_id}")
    await db.execute("INSERT INTO users (vk_id, diary_session) VALUES (?, ?)", (vk_id, diary_session))
    await db.commit()


async def add_user(vk_id: int, login: str, password: str):
    logger.debug(f"Add credentials of user: @id{vk_id}")  # todo
    await db.execute("INSERT INTO users (vk_id, login, password) VALUES (?, ?, ?)", (vk_id, login, password))
    await db.commit()


async def get_user(vk_id: int) -> Optional[Tuple[str, str]]:
    logger.debug(f"Get user: @id{vk_id}")
    async with db.execute("SELECT login, password FROM users WHERE vk_id = ?", (vk_id,)) as cur:
        user: Optional[List[Tuple[str, str]]] = await cur.fetchall()
        return user[0] if user else None


async def get_users() -> List[Tuple[int, Optional[str], Optional[str], Optional[str]]]:
    logger.debug(f"Get all users")
    async with db.execute("SELECT vk_id, diary_session, login, password FROM users") as cur:
        users: Optional[List[Tuple[int, Optional[str], Optional[str], Optional[str]]]] = await cur.fetchall()
        return users if users else []


async def delete_user(vk_id: int):
    logger.debug(f"Delete user: @id{vk_id}")
    await db.execute("DELETE FROM users WHERE vk_id = ?", (vk_id,))
    await db.commit()


async def add_chat(chat_id: int, vk_id: int):
    logger.debug(f"Add chat: {chat_id}")
    await db.execute("INSERT INTO chats (chat_id, vk_id) VALUES (?, ?)", (chat_id, vk_id))
    await db.commit()


async def get_chat(chat_id: int) -> Optional[Tuple[int]]:
    logger.debug(f"Get chat: {chat_id}")
    async with db.execute("SELECT vk_id FROM chats WHERE chat_id = ?", (chat_id,)) as cur:
        chat: Optional[Tuple[int]] = await cur.fetchall()
        return chat[0] if chat else None


async def get_chats() -> List[Tuple[int, int]]:
    logger.debug(f"Get all chats")
    async with db.execute("SELECT chat_id, vk_id FROM chats") as cur:
        chats = await cur.fetchall()
        return chats if chats else []


async def delete_chat(chat_id: int):
    logger.debug(f"Delete chat: {chat_id}")
    await db.execute("DELETE FROM chats WHERE chat_id = ?", (chat_id,))
    await db.commit()
