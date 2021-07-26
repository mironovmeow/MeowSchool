import os
from typing import List, Tuple, Optional

import psycopg2
from psycopg2.extensions import connection, cursor

DATABASE_URL = os.environ['DATABASE_URL']

conn: connection = psycopg2.connect(DATABASE_URL, sslmode='require')


def create_table():
    cur: cursor = conn.cursor()
    cur.execute("""CREATE TABLE users (
    vk_id INT PRIMARY KEY,
    diary_session VARCHAR (32),
    login VARCHAR (128),
    password VARCHAR (128)
);""")
    conn.commit()
    cur.close()


def add_session(vk_id: int, diary_session: str) -> None:
    cur: cursor = conn.cursor()
    cur.execute("INSERT INTO users (vk_id, diary_session) VALUES (%s, %s);", (vk_id, diary_session))
    conn.commit()
    cur.close()


def add_user(vk_id: int, login: str, password: str) -> None:
    cur: cursor = conn.cursor()
    cur.execute("INSERT INTO users (vk_id, login, password) VALUES (%s, %s, %s);", (vk_id, login, password))
    conn.commit()
    cur.close()


# def get_session(vk_id: int) -> typing.Union[str, None]:
#     cur: cursor = conn.cursor()
#     cur.execute("SELECT diary_session FROM users WHERE vk_id = %s;", (vk_id,))
#     session = cur.fetchone()
#     cur.close()
#     if session:
#         return session[0]
#     return None


def get_users() -> List[Tuple[int, Optional[str], Optional[str], Optional[str]]]:
    cur: cursor = conn.cursor()
    cur.execute("SELECT vk_id, diary_session, login, password FROM users")
    users = cur.fetchall()
    cur.close()
    if users:
        return users
    else:
        return []


def delete_session(vk_id: int) -> None:
    cur: cursor = conn.cursor()
    cur.execute("DELETE FROM users WHERE vk_id = %s;", (vk_id,))
    conn.commit()
    cur.close()
