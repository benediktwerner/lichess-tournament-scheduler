from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Optional, cast
import sqlite3
from time import time
from calendar import timegm
from datetime import datetime, timedelta

from flask import current_app

DATABASE = "database.sqlite"


class Db:
    @staticmethod
    def create_tables() -> None:
        with Db() as db:
            with db.db as conn:
                with current_app.open_resource("schema.sql", mode="r") as f:
                    conn.executescript(f.read())

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

    def schedules(self) -> List[ScheduleWithId]:
        return [
            ScheduleWithId._from_row(x) for x in self._query(f"SELECT * FROM schedules")
        ]

    def team_of_schedule(self, id: int) -> Optional[str]:
        row = self._query_one("SELECT team from schedules WHERE id = ?", (id,))
        if row:
            return cast(str, row["team"])
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


@dataclass
class Schedule:
    name: str
    team: str
    clock: int
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
            get_or_raise(j, "clock", int),
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
        now = time()

        if self.scheduleStart and now < self.scheduleStart:
            return None
        if self.scheduleEnd and self.scheduleEnd < now:
            return None

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
        return timegm(new.timetuple())


@dataclass
class ScheduleWithId(Schedule):
    id: int

    @staticmethod
    def _from_row(row: sqlite3.Row) -> ScheduleWithId:
        return ScheduleWithId(**row)  # type: ignore

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


def get_or_raise(j: dict, key: str, typ: type) -> Any:
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
