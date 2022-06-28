from __future__ import annotations

import sqlite3
from time import time
from typing import Any, List, Optional, Tuple

from flask import Flask

from model import Schedule, ScheduleWithId

DATABASE = "database.sqlite"
VERSION = 7


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
                trans.execute(f"PRAGMA user_version = {VERSION}")
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

    def insert_created(self, id: str, schedule_id: int, team: str, t: int) -> None:
        with self.db as conn:
            conn.execute(
                """INSERT INTO createdArenas (
                    id,
                    scheduleId,
                    team,
                    time
                   ) VALUES (?, ?, ?, ?)
                """,
                (id, schedule_id, team, t),
            )

    def delete_created(self, id: str) -> None:
        with self.db as conn:
            conn.execute("DELETE FROM createdArenas WHERE id = ?", (id,))

    def team_of_created(self, id: str) -> Optional[str]:
        a = self._query_one("SELECT team FROM createdArenas WHERE id = ?", (id,))
        if a:
            return str(a["team"])
        return None

    def created_upcoming(self) -> List[Tuple[str, str]]:
        rows = self._query(
            "SELECT id, team FROM createdArenas WHERE time > ?", (int(time()),)
        )
        return [(row["id"], row["team"]) for row in rows]

    def created_upcoming_with_schedule(self, schedule_id: int) -> List[str]:
        rows = self._query(
            "SELECT id FROM createdArenas WHERE scheduleId = ? and time > ? ORDER BY time ASC",
            (schedule_id, int(time())),
        )
        return [row["id"] for row in rows]

    def previous_created(self, schedule_id: int, timestamp: int) -> Optional[str]:
        result = self._query_one(
            "SELECT id FROM createdArenas WHERE scheduleId = ? and time < ? ORDER BY time DESC LIMIT 1",
            (schedule_id, timestamp),
        )
        return result["id"] if result else None

    def prev_nxt_of_created(self, id: str) -> Tuple[Optional[str], Optional[str]]:
        result = self._query_one(
            "SELECT scheduleId, time FROM createdArenas WHERE id = ?",
            (id,),
        )
        if not result:
            return (None, None)
        prev = self._query_one(
            "SELECT id FROM createdArenas WHERE scheduleId = ? and time < ? ORDER BY time DESC LIMIT 1",
            (result["scheduleId"], result["time"]),
        )
        nxt = self._query_one(
            "SELECT id FROM createdArenas WHERE scheduleId = ? and time > ? ORDER BY time DESC LIMIT 1",
            (result["scheduleId"], result["time"]),
        )
        return (prev["id"] if prev else None, nxt["id"] if nxt else None)

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
                    scheduleEnd,
                    teamBattleTeams,
                    teamBattleLeaders,
                    daysInAdvance
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    s.teamBattleTeams,
                    s.teamBattleLeaders,
                    s.daysInAdvance,
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
                    scheduleEnd = ?,
                    teamBattleTeams = ?,
                    teamBattleLeaders = ?,
                    daysInAdvance = ?
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
                    s.teamBattleTeams,
                    s.teamBattleLeaders,
                    s.daysInAdvance,
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
                (text, int(time() * 1_000_000)),
            )

    def clean_logs(self) -> None:
        with self.db as conn:
            conn.execute(
                "DELETE FROM logs WHERE time < ?",
                (int(time() * 1_000_000) - 31 * 24 * 60 * 60 * 1_000_000,),
            )

    def logs(self) -> List[Tuple[int, str]]:
        logs = self._query("SELECT * FROM logs")
        return [(r["time"], r["text"]) for r in logs]
