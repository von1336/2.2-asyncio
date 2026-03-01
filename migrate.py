"""
Скрипт миграции: создаёт таблицу people в SQLite.
"""
import sqlite3
import os

DB_PATH = os.environ.get("SWAPI_DB", "swapi.db")

def migrate():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY,
            birth_year TEXT,
            eye_color TEXT,
            gender TEXT,
            hair_color TEXT,
            homeworld TEXT,
            mass TEXT,
            name TEXT,
            skin_color TEXT
        )
    """)
    conn.commit()
    conn.close()
    print(f"Migration done. Database: {DB_PATH}")

if __name__ == "__main__":
    migrate()
