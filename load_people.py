"""
Асинхронная загрузка всех персонажей SWAPI в SQLite.
Сначала получаем список всех id из /api/people, затем асинхронно загружаем детали по каждому.
"""
import asyncio
import aiohttp
import aiosqlite
import os

DB_PATH = os.environ.get("SWAPI_DB", "swapi.db")
BASE_URL = "https://www.swapi.tech/api/people"


async def get_all_people_ids(session: aiohttp.ClientSession) -> list[int]:
    """Получить список всех id персонажей из API."""
    ids = []
    page = 1
    while True:
        async with session.get(f"{BASE_URL}?page={page}&limit=100") as resp:
            if resp.status != 200:
                break
            data = await resp.json()
            if data.get("message") != "ok" or "results" not in data:
                break
            results = data["results"]
            if not results:
                break
            for item in results:
                uid = item.get("uid")
                if uid is not None:
                    ids.append(int(uid))
            if data.get("next") is None:
                break
            page += 1
    return ids


async def fetch_person(session: aiohttp.ClientSession, uid: int) -> dict | None:
    url = f"{BASE_URL}/{uid}/"
    try:
        async with session.get(url) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            if data.get("message") != "ok" or "result" not in data:
                return None
            props = data["result"].get("properties", {})
            return {
                "id": int(data["result"].get("uid", uid)),
                "birth_year": props.get("birth_year"),
                "eye_color": props.get("eye_color"),
                "gender": props.get("gender"),
                "hair_color": props.get("hair_color"),
                "homeworld": props.get("homeworld"),
                "mass": props.get("mass"),
                "name": props.get("name"),
                "skin_color": props.get("skin_color"),
            }
    except Exception:
        return None


async def save_person(db: aiosqlite.Connection, person: dict) -> None:
    await db.execute(
        """
        INSERT OR REPLACE INTO people (id, birth_year, eye_color, gender, hair_color, homeworld, mass, name, skin_color)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            person["id"],
            person.get("birth_year"),
            person.get("eye_color"),
            person.get("gender"),
            person.get("hair_color"),
            person.get("homeworld"),
            person.get("mass"),
            person.get("name"),
            person.get("skin_color"),
        ),
    )


async def load_all() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        async with aiohttp.ClientSession() as session:
            print("Получение списка персонажей...")
            ids = await get_all_people_ids(session)
            print(f"Найдено персонажей: {len(ids)}")

            tasks = [fetch_person(session, uid) for uid in ids]
            results = await asyncio.gather(*tasks)

            count = 0
            for person in results:
                if person:
                    await save_person(db, person)
                    count += 1
            await db.commit()
            print(f"Загружено в БД: {count} персонажей. Файл: {DB_PATH}")


if __name__ == "__main__":
    asyncio.run(load_all())
