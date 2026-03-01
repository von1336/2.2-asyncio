# Домашнее задание 2.2 — Asyncio

Выгрузка персонажей Star Wars из [SWAPI](https://swapi.tech/) и загрузка в БД асинхронно.

1. `migrate.py` — создание таблицы в SQLite.
2. `load_people.py` — асинхронная загрузка всех персонажей из API в БД.

Запуск:
```bash
pip install -r requirements.txt
python migrate.py
python load_people.py
```
