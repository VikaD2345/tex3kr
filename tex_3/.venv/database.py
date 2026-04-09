"""Модуль работы с базой данных SQLite."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "control_work.db"


def get_db_connection():
    """Создаёт и возвращает подключение к БД."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Инициализирует таблицы БД."""
    with get_db_connection() as conn:
        # Таблица пользователей (Задание 8.1)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        """)
        # Таблица Todo (Задание 8.2)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT,
                completed BOOLEAN DEFAULT 0,
                owner_username TEXT NOT NULL,
                FOREIGN KEY (owner_username) REFERENCES users (username)
            )
        """)
        conn.commit()


@contextmanager
def get_db_cursor():
    """Контекстный менеджер для работы с курсором БД."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()