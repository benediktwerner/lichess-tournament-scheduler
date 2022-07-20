from __future__ import annotations

import logging
import sqlite3
from time import time
from typing import Any, List, Optional, Set, Tuple

from flask import Flask

from model import ArenaEdit, MsgToSend, Schedule, ScheduleWithId

DATABASE = "database.sqlite"
VERSION = 8


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class Db:
    def create_tables(self, app: Flask) -> None:
        sqlite_schema = (
            "sqlite_schema"
            if sqlite3.sqlite_version_info >= (3, 33, 0)
            else "sqlite_master"
        )
        if not self._query(f"SELECT * FROM {sqlite_schema}"):
            logger.info("No tables. Initializing database schema.")
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

        logger.info(f"Db schema version is {version}. Migrating up to {VERSION}.")

        with self.db as trans:
            while version < VERSION:
                version += 1
                logger.info(f"Migrating to {version}")
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

    def update_created(self, arena: ArenaEdit) -> None:
        with self.db as conn:
            conn.execute(
                "UPDATE createdArenas SET time = ? WHERE id = ?",
                (arena.startsAt, arena.id),
            )
            conn.execute(
                "UPDATE scheduledMsgs SET sendTime = ? - (60 * minutesBefore) WHERE arenaId = ?",
                (arena.startsAt, arena.id),
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

    def get_scheduled(self) -> Set[Tuple[int, int]]:
        rows = self._query("SELECT scheduleId, time FROM createdArenas WHERE time > ?", (int(time()),))
        return set((row["scheduleId"], row["time"]) for row in rows)

    def previous_created(self, schedule_id: int, timestamp: int) -> Optional[str]:
        result = self._query_one(
            "SELECT id FROM createdArenas WHERE scheduleId = ? and time < ? ORDER BY time DESC LIMIT 1",
            (schedule_id, timestamp),
        )
        return result["id"] if result else None

    def previous_two_created(self, schedule_id: int, timestamp: int) -> Tuple[Optional[str], Optional[str]]:
        rows = self._query(
            "SELECT id FROM createdArenas WHERE scheduleId = ? and time < ? ORDER BY time DESC LIMIT 2",
            (schedule_id, timestamp),
        )
        prevs = [row["id"] for row in rows]
        if len(prevs) < 1:
            return None, None
        if len(prevs) == 1:
            return prevs[0], None
        return prevs[0], prevs[1]


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
                    daysInAdvance,
                    msgMinutesBefore,
                    msgTemplate,
                    msgToken
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    s.msgMinutesBefore,
                    s.msgTemplate,
                    s.msgToken,
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
                    daysInAdvance = ?,
                    msgMinutesBefore = ?,
                    msgTemplate = ?,
                    msgToken = ?
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
                    s.msgMinutesBefore,
                    s.msgTemplate,
                    s.msgToken,
                    s.id,
                    s.team,
                ),
            )

    def delete_schedule(self, id: int) -> None:
        with self.db as conn:
            conn.execute("DELETE FROM schedules WHERE id = ?", (id,))

    def insert_scheduled_msg(
        self,
        arenaId: str,
        scheduleId: int,
        team: str,
        template: str,
        token: str,
        minutesBefore: int,
        sendTime: int,
    ) -> None:
        with self.db as conn:
            conn.execute(
                "INSERT INTO scheduledMsgs (arenaId, scheduleId, team, template, token, minutesBefore, sendTime) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (arenaId, scheduleId, team, template, token, minutesBefore, sendTime),
            )

    def get_and_remove_scheduled_msgs(self) -> List[MsgToSend]:
        now = int(time())
        rows = self._query(
            "SELECT arenaId, team, template, token FROM scheduledMsgs WHERE sendTime < ? AND sendTime > ?",
            (now, now - 30 * 60),
        )
        msgs = [
            MsgToSend(row["arenaId"], row["team"], row["template"], row["token"])
            for row in rows
        ]
        with self.db as conn:
            conn.execute("DELETE FROM scheduledMsgs WHERE sendTime < ?", (now,))
        return msgs

    def update_scheduled_msgs(self, schedule: ScheduleWithId) -> None:
        with self.db as conn:
            conn.execute(
                "DELETE FROM scheduledMsgs WHERE scheduleId = ?", (schedule.id,)
            )
            if (
                schedule.msgMinutesBefore
                and schedule.msgMinutesBefore > 0
                and schedule.msgTemplate
                and schedule.msgToken
            ):
                conn.execute(
                    """INSERT INTO scheduledMsgs (arenaId, scheduleId, team, template, token, sendTime) 
                            SELECT id, scheduleId, team, ?, ?, time - ? FROM createdArenas WHERE scheduleId = ?
                        """,
                    (
                        schedule.msgTemplate,
                        schedule.msgToken,
                        schedule.msgMinutesBefore,
                        schedule.id,
                    ),
                )

    def insert_bad_token(self, token: str, team: str) -> None:
        with self.db as conn:
            conn.execute(
                "INSERT INTO badTokens (token, team) VALUES (?, ?)", (token, team)
            )

    def bad_tokens(self) -> Set[str]:
        return set(
            (row["token"], row["team"])
            for row in self._query("SELECT token, team FROM badTokens")
        )

    def bad_tokens_for_team(self, team: str) -> List[str]:
        return set(
            row["token"]
            for row in self._query(
                "SELECT token FROM badTokens WHERE team = ?", (team,)
            )
        )

    def replace_token_for_team(self, team: str, token: str) -> None:
        bad_tokens = self.bad_tokens_for_team(team)
        with self.db as conn:
            for t in bad_tokens:
                conn.execute(
                    "UPDATE schedules SET msgToken = ? WHERE team = ? AND msgToken = ?",
                    (token, team, t),
                )
                conn.execute(
                    "UPDATE scheduledMsgs SET token = ? WHERE team = ? AND token = ?",
                    (token, team, t),
                )
            conn.execute("DELETE FROM badTokens WHERE team = ?", (team,))
