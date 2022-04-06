from __future__ import annotations

import sqlite3
from calendar import timegm
from dataclasses import dataclass
from datetime import datetime, timedelta
from time import time
from typing import Any, List, Optional, Tuple

from flask import Flask

DATABASE = "database.sqlite"
VERSION = 2


class Db:
    def create_tables(self, app: Flask) -> None:
        sqlite_schema = (
            "sqlite_schema"
            if sqlite3.sqlite_version_info >= (3, 33, 0)
            else "sqlite_master"
        )
        if not self._query(f"SELECT * FROM {sqlite_schema}"):
            app.logger.info("No tables. Initializing database schema.")
            with self.db as trans:
                with app.open_resource("schema.sql", mode="r") as f:
                    trans.executescript(f.read())
            return

        version = self._version()
        if version == VERSION:
            return

        if version > VERSION:
            raise Exception(
                f"Db schema version is {version} which is higher than the latest known version ({VERSION})."
            )

        app.logger.info(f"Db schema version is {version}. Migrating up to {VERSION}.")

        with self.db as trans:
            while version < VERSION:
                version += 1
                app.logger.info(f"Migrating to {version}")
                with app.open_resource(f"migrations/{version}.sql", mode="r") as f:
                    trans.executescript(f.read())
            trans.execute(f"PRAGMA user_version = {VERSION}")

    def _version(self) -> int:
        version = self._query_one("PRAGMA user_version")
        if version is None:
            raise Exception("pragma user_version returned None")
        return version[0]

    def __enter__(self) -> Db:
        self.db = sqlite3.connect(DATABASE)
        self.db.row_factory = sqlite3.Row
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, exc_traceback: Any) -> None:
        self.db.close()

    def _query(self, query: str, args: tuple = ()) -> List[sqlite3.Row]:
        return self.db.execute(query, args).fetchall()

    def _query_one(self, query: str, args: tuple = ()) -> Optional[sqlite3.Row]:
        result = self._query(query, args)
        return result[0] if result else None

    def insert_created(self, id: str, team: str, t: int) -> None:
        with self.db as conn:
            conn.execute(
                """INSERT INTO createdArenas (
                    id,
                    team,
                    time
                   ) VALUES (?, ?, ?)
                """,
                (id, team, t),
            )

    def delete_created(self, id: str) -> None:
        with self.db as conn:
            conn.execute("DELETE FROM createdArenas WHERE id = ?", (id,))

    def delete_past_created(self) -> None:
        with self.db as conn:
            conn.execute("DELETE FROM createdArenas WHERE time < ?", (int(time()),))

    def team_of_created(self, id: str) -> Optional[str]:
        a = self._query_one("SELECT team FROM createdArenas WHERE id = ?", (id,))
        if a:
            return str(a["team"])
        return None

    def schedules(self) -> List[ScheduleWithId]:
        return [
            ScheduleWithId._from_row(x) for x in self._query(f"SELECT * FROM schedules")
        ]

    def team_of_schedule(self, id: int) -> Optional[str]:
        row = self._query_one("SELECT team from schedules WHERE id = ?", (id,))
        if row:
            return str(row["team"])
        return None

    def insert_schedule(self, s: Schedule) -> None:
        with self.db as conn:
            conn.execute(
                """INSERT INTO schedules (
                    name,
                    team,
                    clock,
                    increment,
                    minutes,
                    variant,
                    rated,
                    position,
                    berserkable,
                    streakable,
                    description,
                    minRating,
                    maxRating,
                    minGames,
                    scheduleDay,
                    scheduleTime,
                    scheduleStart,
                    scheduleEnd
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    s.name,
                    s.team,
                    s.clock,
                    s.increment,
                    s.minutes,
                    s.variant,
                    s.rated,
                    s.position,
                    s.berserkable,
                    s.streakable,
                    s.description,
                    s.minRating,
                    s.maxRating,
                    s.minGames,
                    s.scheduleDay,
                    s.scheduleTime,
                    s.scheduleStart,
                    s.scheduleEnd,
                ),
            )

    def update_schedule(self, s: ScheduleWithId) -> None:
        with self.db as conn:
            conn.execute(
                """UPDATE schedules SET
                    name = ?,
                    clock = ?,
                    increment = ?,
                    minutes = ?,
                    variant = ?,
                    rated = ?,
                    position = ?,
                    berserkable = ?,
                    streakable = ?,
                    description = ?,
                    minRating = ?,
                    maxRating = ?,
                    minGames = ?,
                    scheduleDay = ?,
                    scheduleTime = ?,
                    scheduleStart = ?,
                    scheduleEnd = ?
                   WHERE id = ? and team = ?
                """,
                (
                    s.name,
                    s.clock,
                    s.increment,
                    s.minutes,
                    s.variant,
                    s.rated,
                    s.position,
                    s.berserkable,
                    s.streakable,
                    s.description,
                    s.minRating,
                    s.maxRating,
                    s.minGames,
                    s.scheduleDay,
                    s.scheduleTime,
                    s.scheduleStart,
                    s.scheduleEnd,
                    s.id,
                    s.team,
                ),
            )

    def delete_schedule(self, id: int) -> None:
        with self.db as conn:
            conn.execute("DELETE FROM schedules WHERE id = ?", (id,))

    def add_log(self, text: str) -> None:
        with self.db as conn:
            conn.execute(
                """INSERT INTO logs (
                    text,
                    time
                   ) VALUES (?, ?)
                """,
                (text, int(time() * 1000)),
            )

    def clean_logs(self) -> None:
        with self.db as conn:
            conn.execute(
                "DELETE FROM logs WHERE time < ?",
                (int(time() * 1_000_000) - 7 * 24 * 60 * 60 * 1_000_000,),
            )

    def logs(self) -> List[Tuple[int, str]]:
        logs = self._query("SELECT * FROM logs")
        return [(r["time"], r["text"]) for r in logs]


@dataclass
class Schedule:
    name: str
    team: str
    clock: float
    increment: int
    minutes: int  # duration
    variant: str
    rated: bool
    position: Optional[str]
    berserkable: bool
    streakable: bool
    description: Optional[str]
    minRating: Optional[int]
    maxRating: Optional[int]
    minGames: Optional[int]
    scheduleDay: int
    scheduleTime: int
    scheduleStart: Optional[int]
    scheduleEnd: Optional[int]

    @property
    def scheduleHour(self) -> int:
        return self.scheduleTime // 60

    @property
    def scheduleMinute(self) -> int:
        return self.scheduleTime % 60

    @staticmethod
    def from_json(j: dict) -> Schedule:
        return Schedule(
            get_or_raise(j, "name", str),
            get_or_raise(j, "team", str),
            float(get_or_raise(j, "clock", (int, float))),
            get_or_raise(j, "increment", int),
            get_or_raise(j, "minutes", int),
            get_or_raise(j, "variant", str),
            get_or_raise(j, "rated", bool),
            get_opt_or_raise(j, "position", str),
            get_or_raise(j, "berserkable", bool),
            get_or_raise(j, "streakable", bool),
            get_opt_or_raise(j, "description", str),
            get_opt_or_raise(j, "minRating", int),
            get_opt_or_raise(j, "maxRating", int),
            get_opt_or_raise(j, "minGames", int),
            get_or_raise(j, "scheduleDay", int),
            get_or_raise(j, "scheduleTime", int),
            get_opt_or_raise(j, "scheduleStart", int),
            get_opt_or_raise(j, "scheduleEnd", int),
        )

    def next_time(self) -> Optional[int]:
        date = datetime.utcnow()
        new = date.replace(
            hour=self.scheduleHour,
            minute=self.scheduleMinute,
            second=0,
            microsecond=0,
        )

        if self.scheduleDay == 0:
            if new < date:
                new += timedelta(days=1)
        else:
            new += timedelta(days=self.scheduleDay - date.isoweekday())
            if new < date:
                new += timedelta(days=7)

        nxt = timegm(new.timetuple())

        if self.scheduleStart and nxt < self.scheduleStart:
            return None
        if self.scheduleEnd and self.scheduleEnd < nxt:
            return None

        return nxt


@dataclass
class ScheduleWithId(Schedule):
    id: int

    @staticmethod
    def _from_row(row: sqlite3.Row) -> ScheduleWithId:
        s = ScheduleWithId(**row)  # type: ignore
        s.rated = bool(s.rated)
        s.berserkable = bool(s.berserkable)
        s.streakable = bool(s.streakable)
        return s

    @staticmethod
    def from_json(j: dict) -> ScheduleWithId:
        s = Schedule.from_json(j)
        return ScheduleWithId(
            s.name,
            s.team,
            s.clock,
            s.increment,
            s.minutes,
            s.variant,
            s.rated,
            s.position,
            s.berserkable,
            s.streakable,
            s.description,
            s.minRating,
            s.maxRating,
            s.minGames,
            s.scheduleDay,
            s.scheduleTime,
            s.scheduleStart,
            s.scheduleEnd,
            get_or_raise(j, "id", int),
        )


class ParseError(Exception):
    pass


def get_or_raise(j: dict, key: str, typ: type | tuple[type, type]) -> Any:
    if key not in j:
        raise ParseError(f"Missing key: {key}")
    val = j[key]
    if not isinstance(val, typ):
        raise ParseError(f"Invalid value for {key}: {val}")
    return val


def get_opt_or_raise(j: dict, key: str, typ: type) -> Any:
    val = j.get(key)
    if val is not None and not isinstance(val, typ):
        raise ParseError(f"Invalid value for {key}: {val}")
    return val
