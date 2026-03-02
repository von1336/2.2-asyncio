"""
Асинхронная загрузка всех персонажей SWAPI в SQLite.
Список id из /api/people, затем детали по каждому. homeworld — название планеты (по URL).
"""
from __future__ import annotations
import asyncio
import logging
import aiohttp
import aiosqlite
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

DB_PATH = os.environ.get("SWAPI_DB", "swapi.db")
BASE_URL = "https://www.swapi.tech/api/people"

# Ограничение одновременных запросов к API
SEMAPHORE_LIMIT = 10
# Повторные попытки при ошибке сети
MAX_RETRIES = 3
RETRY_DELAY = 1.0

semaphore = asyncio.Semaphore(SEMAPHORE_LIMIT)


async def get_planet_name(session: aiohttp.ClientSession, url: str | None) -> str:
    """Получить название планеты по URL."""
    if not url:
        return ""
    for attempt in range(MAX_RETRIES):
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    props = data.get("result", {}).get("properties", {})
                    return props.get("name", url)
        except Exception as e:
            logger.debug("get_planet_name %s attempt %s: %s", url, attempt + 1, e)
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(RETRY_DELAY)
    return url  # fallback — оставляем URL при неудаче


async def get_all_people_ids(session: aiohttp.ClientSession) -> list[int]:
    """Получить список всех id персонажей из API."""
    ids = []
    page = 1
    while True:
        try:
            async with session.get(f"{BASE_URL}?page={page}&limit=100") as resp:
                if resp.status != 200:
                    logger.warning("Список персонажей: HTTP %s", resp.status)
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
        except Exception as e:
            logger.exception("Ошибка при получении списка: %s", e)
            break
    return ids


async def fetch_person(session: aiohttp.ClientSession, uid: int) -> dict | None:
    """Загрузить данные одного персонажа. mass может быть 'unknown' (строка)."""
    async with semaphore:
        url = f"{BASE_URL}/{uid}/"
        for attempt in range(MAX_RETRIES):
            try:
                async with session.get(url) as resp:
                    if resp.status != 200:
                        if attempt < MAX_RETRIES - 1:
                            await asyncio.sleep(RETRY_DELAY)
                            continue
                        return None
                    data = await resp.json()
                    if data.get("message") != "ok" or "result" not in data:
                        return None
                    props = data["result"].get("properties", {})

                    homeworld_url = props.get("homeworld")
                    homeworld_name = await get_planet_name(session, homeworld_url)

                    return {
                        "id": int(data["result"].get("uid", uid)),
                        "birth_year": props.get("birth_year"),
                        "eye_color": props.get("eye_color"),
                        "gender": props.get("gender"),
                        "hair_color": props.get("hair_color"),
                        "homeworld": homeworld_name,
                        "mass": props.get("mass"),  # может быть "unknown"
                        "name": props.get("name"),
                        "skin_color": props.get("skin_color"),
                    }
            except Exception as e:
                logger.debug("fetch_person uid=%s attempt %s: %s", uid, attempt + 1, e)
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(RETRY_DELAY)
                else:
                    logger.warning("Не удалось загрузить персонажа uid=%s: %s", uid, e)
                    return None
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
    logger.info("Старт загрузки. БД: %s", DB_PATH)
    async with aiosqlite.connect(DB_PATH) as db:
        async with aiohttp.ClientSession() as session:
            logger.info("Получение списка персонажей...")
            ids = await get_all_people_ids(session)
            logger.info("Найдено персонажей: %s", len(ids))

            tasks = [fetch_person(session, uid) for uid in ids]
            results = await asyncio.gather(*tasks)

            count = 0
            for person in results:
                if person:
                    await save_person(db, person)
                    count += 1
            await db.commit()
            logger.info("Загружено в БД: %s персонажей. Файл: %s", count, DB_PATH)


if __name__ == "__main__":
    asyncio.run(load_all())
