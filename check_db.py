"""Проверка: homeworld — название планеты, mass может быть unknown."""
import sqlite3
import os

DB = os.environ.get("SWAPI_DB", "swapi.db")
conn = sqlite3.connect(DB)
rows = conn.execute("SELECT id, name, homeworld, mass FROM people LIMIT 10").fetchall()
print("Пример записей (id, name, homeworld, mass):")
for r in rows:
    print(r)
url_count = conn.execute(
    "SELECT COUNT(*) FROM people WHERE homeworld LIKE 'https://%'"
).fetchone()[0]
print("\nЗаписей, где homeworld всё ещё URL:", url_count)
print("Всего записей:", conn.execute("SELECT COUNT(*) FROM people").fetchone()[0])
conn.close()
