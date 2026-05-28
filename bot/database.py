import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "kinozona.db")


class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()

    def _create_tables(self):
        cursor = self.conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_banned INTEGER DEFAULT 0,
                joined_at TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS movies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                file_id TEXT,
                year TEXT,
                genre TEXT,
                rating REAL,
                duration TEXT,
                size TEXT,
                description TEXT,
                category TEXT DEFAULT 'boshqa',
                quality TEXT DEFAULT 'HD',
                language TEXT DEFAULT "O'zbek tilida",
                added_by INTEGER,
                added_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
        """)
        self.conn.commit()

    def add_user(self, user_id, username, first_name, last_name):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT OR IGNORE INTO users (id, username, first_name, last_name)
                   VALUES (?, ?, ?, ?)""",
                (user_id, username, first_name, last_name)
            )
            self.conn.commit()
        except Exception as e:
            print(f"add_user error: {e}")

    def is_banned(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT is_banned FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return bool(row and row["is_banned"])

    def ban_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET is_banned = 1 WHERE id = ?", (user_id,))
        self.conn.commit()

    def unban_user(self, user_id):
        cursor = self.conn.cursor()
        cursor.execute("UPDATE users SET is_banned = 0 WHERE id = ?", (user_id,))
        self.conn.commit()

    def get_all_movies(self, category=None):
        cursor = self.conn.cursor()
        if category:
            cursor.execute(
                "SELECT * FROM movies WHERE category = ? ORDER BY added_at DESC",
                (category,)
            )
        else:
            cursor.execute("SELECT * FROM movies ORDER BY added_at DESC")
        return [dict(row) for row in cursor.fetchall()]

    def get_movie(self, movie_id=None, code=None):
        cursor = self.conn.cursor()
        if movie_id:
            cursor.execute("SELECT * FROM movies WHERE id = ?", (movie_id,))
        elif code:
            cursor.execute("SELECT * FROM movies WHERE code = ?", (code,))
        else:
            return None
        row = cursor.fetchone()
        return dict(row) if row else None

    def search_movies(self, query):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM movies WHERE title LIKE ? OR code LIKE ? ORDER BY added_at DESC",
            (f"%{query}%", f"%{query}%")
        )
        return [dict(row) for row in cursor.fetchall()]

    def add_movie(self, code, title, file_id=None, year=None, genre=None,
                  rating=None, duration=None, size=None, description=None,
                  category="boshqa", quality="HD", added_by=None, **kwargs):
        try:
            cursor = self.conn.cursor()
            cursor.execute(
                """INSERT INTO movies
                   (code, title, file_id, year, genre, rating, duration, size,
                    description, category, quality, added_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (code, title, file_id, year, genre, rating, duration, size,
                 description, category, quality, added_by)
            )
            self.conn.commit()
            return True
        except Exception as e:
            print(f"add_movie error: {e}")
            return False

    def delete_movie(self, movie_id):
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM movies WHERE id = ?", (movie_id,))
            self.conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"delete_movie error: {e}")
            return False

    def get_all_users(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM users WHERE is_banned = 0")
        return [dict(row) for row in cursor.fetchall()]

    def get_stats(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM movies")
        total_movies = cursor.fetchone()["cnt"]
        cursor.execute("SELECT COUNT(*) as cnt FROM users")
        total_users = cursor.fetchone()["cnt"]
        return {"total_movies": total_movies, "total_users": total_users}


db = Database()
