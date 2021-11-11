"""
Module to working with database (sqlite3)
"""
# TODO add cryptography

import sqlite3
import typing

from vkbottle.modules import logger

conn = sqlite3.connect('db.sqlite3')


def create_tables() -> None:
    logger.debug("Create table")
    cur = conn.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users (
    vk_id INT PRIMARY KEY,
    diary_session VARCHAR (32),
    login VARCHAR (128),
    password VARCHAR (128)
);""")
    cur.execute("""CREATE TABLE IF NOT EXISTS chats (
    chat_id INT PRIMARY KEY,
    vk_id INT NOT NULL
);""")
    conn.commit()
    cur.close()


def add_session(vk_id: int, diary_session: str) -> None:
    logger.debug(f"Add session of user: @id{vk_id}")
    cur = conn.cursor()
    cur.execute("INSERT INTO users (vk_id, diary_session) VALUES (?, ?);", (vk_id, diary_session))
    conn.commit()
    cur.close()


def add_user(vk_id: int, login: str, password: str) -> None:
    logger.debug(f"Add credentials of user: @id{vk_id}")
    cur = conn.cursor()
    cur.execute("INSERT INTO users (vk_id, login, password) VALUES (?, ?, ?);", (vk_id, login, password))
    conn.commit()
    cur.close()


def get_user(vk_id: int) -> typing.Optional[str]:
    logger.debug(f"Get user: @id{vk_id}")
    cur = conn.cursor()
    cur.execute("SELECT login, password FROM users WHERE vk_id = (?);", (vk_id,))
    user = cur.fetchall()
    cur.close()
    if user:  # None check
        return user[0]
    return None


def get_users() -> typing.List[typing.Tuple[int, typing.Optional[str], typing.Optional[str], typing.Optional[str]]]:
    logger.debug(f"Get all users")
    cur = conn.cursor()
    cur.execute("SELECT vk_id, diary_session, login, password FROM users;")
    users = cur.fetchall()
    cur.close()
    if users:  # None check
        return users
    return []


def delete_user(vk_id: int) -> None:
    logger.debug(f"Delete user: @id{vk_id}")
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE vk_id = ?;", (vk_id,))
    conn.commit()
    cur.close()


def add_chat(chat_id: int, vk_id: int) -> None:
    logger.debug(f"Add chat: {chat_id}")
    cur = conn.cursor()
    cur.execute("INSERT INTO chats (chat_id, vk_id) VALUES (?, ?);", (chat_id, vk_id))
    conn.commit()
    cur.close()


def get_chat(chat_id: int) -> typing.Optional[int]:
    logger.debug(f"Get chat: {chat_id}")
    cur = conn.cursor()
    cur.execute("SELECT vk_id FROM chats WHERE chat_id = (?);", (chat_id,))
    user = cur.fetchall()
    cur.close()
    if user:  # None check
        return user[0]
    return None


def get_chats() -> typing.List[typing.Tuple[int, int]]:
    logger.debug(f"Get all chats")
    cur = conn.cursor()
    cur.execute("SELECT chat_id, vk_id FROM chats;")
    chats = cur.fetchall()
    cur.close()
    if chats:  # None check
        return chats
    return []


def delete_chat(chat_id: int) -> None:
    logger.debug(f"Delete chat: @id{chat_id}")
    cur = conn.cursor()
    cur.execute("DELETE FROM chats WHERE chat_id = ?;", (chat_id,))
    conn.commit()
    cur.close()
