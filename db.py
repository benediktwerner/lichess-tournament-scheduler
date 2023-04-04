from __future__ import annotations

import logging
import sqlite3
from time import time
from typing import Any, List, Optional, Set, Tuple

from flask import Flask

from model import CreatedArena, MsgToSend, Schedule, ScheduleWithId

DATABASE = "database.sqlite"
VERSION = 11


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
                    trans.executescript("BEGIN;" + f.read())
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

        while version < VERSION:
            version += 1
            logger.info(f"Migrating to {version}")
            with self.db as trans:
                with app.open_resource(f"migrations/{version}.sql", mode="r") as f:
                    trans.executescript("BEGIN;" + f.read())
                trans.execute(f"PRAGMA user_version = {version}")

    def _version(self) -> int:
        version = self._query_one("PRAGMA user_version")
        if version is None:
            raise Exception("pragma user_version returned None")
        return int(version[0])

    def __enter__(self) -> Db:
        self.db = sqlite3.connect(DATABASE)
        self.db.row_factory = sqlite3.Row
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, exc_traceback: Any) -> None:
        self.db.close()

    def _begin(self) -> None:
        self.db.execute("BEGIN")

    def _query(self, query: str, args: tuple = ()) -> List[sqlite3.Row]:
        return self.db.execute(query, args).fetchall()

    def _query_one(self, query: str, args: tuple = ()) -> Optional[sqlite3.Row]:
        result = self._query(query, args)
        return result[0] if result else None

    def insert_created(
        self, id: str, schedule_id: int, team: str, t: int, error: Optional[str] = None
    ) -> None:
        with self.db as conn:
            conn.execute(
                """INSERT INTO createdArenas (
                    id,
                    scheduleId,
                    team,
                    time,
                    error
                   ) VALUES (?, ?, ?, ?, ?)
                """,
                (id, schedule_id, team, t, error),
            )

    def update_created(self, arena: CreatedArena) -> None:
        with self.db as conn:
            conn.execute(
                "UPDATE createdArenas SET time = ? WHERE id = ?",
                (arena.time, arena.id),
            )

    def delete_created(self, id: str) -> None:
        with self.db as conn:
            self._begin()
            conn.execute("DELETE FROM createdArenas WHERE id = ?", (id,))
            conn.execute("DELETE FROM scheduledMsgs WHERE arenaId = ?", (id,))

    def created(self, id: str) -> Optional[CreatedArena]:
        row = self._query_one(
            "SELECT id, scheduleId, team, time FROM createdArenas WHERE id = ?", (id,)
        )
        if row:
            return CreatedArena.from_row(row)
        return None

    def created_upcoming(self) -> List[Tuple[str, str]]:
        rows = self._query(
            "SELECT id, team FROM createdArenas WHERE time > ?", (int(time()),)
        )
        return [(row["id"], row["team"]) for row in rows]

    def created_upcoming_with_schedule(self, schedule_id: int) -> List[Tuple[str, int]]:
        rows = self._query(
            "SELECT id, time FROM createdArenas WHERE scheduleId = ? and time > ? ORDER BY time ASC",
            (schedule_id, int(time())),
        )
        return [(row["id"], row["time"]) for row in rows]

    def get_scheduled(self) -> Set[Tuple[int, int]]:
        rows = self._query(
            "SELECT scheduleId, time FROM createdArenas WHERE time > ?", (int(time()),)
        )
        return set((row["scheduleId"], row["time"]) for row in rows)

    def num_created_before(self, schedule_id: int, timestamp: int) -> int:
        result = self._query_one(
            "SELECT COUNT(*) FROM createdArenas WHERE scheduleId = ? AND time < ?",
            (schedule_id, timestamp),
        )
        if result:
            return int(result[0])
        return 0

    def previous_created(self, schedule_id: int, timestamp: int) -> Optional[str]:
        result = self._query_one(
            "SELECT id FROM createdArenas WHERE scheduleId = ? and time < ? ORDER BY time DESC LIMIT 1",
            (schedule_id, timestamp),
        )
        return result["id"] if result else None

    def previous_two_created(
        self, schedule_id: int, timestamp: int
    ) -> Tuple[Optional[str], Optional[str]]:
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

    def schedules(self) -> List[ScheduleWithId]:
        return [
            ScheduleWithId.from_row(x) for x in self._query(f"SELECT * FROM schedules")
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
                    teamBattleAlternativeTeamsEnabled,
                    teamBattleAlternativeTeams,
                    teamBattleLeaders,
                    daysInAdvance,
                    msgMinutesBefore,
                    msgTemplate
                   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    s.teamBattleAlternativeTeamsEnabled,
                    s.teamBattleAlternativeTeams,
                    s.teamBattleLeaders,
                    s.daysInAdvance,
                    s.msgMinutesBefore,
                    s.msgTemplate,
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
                    teamBattleAlternativeTeamsEnabled = ?,
                    teamBattleAlternativeTeams = ?,
                    teamBattleLeaders = ?,
                    daysInAdvance = ?,
                    msgMinutesBefore = ?,
                    msgTemplate = ?
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
                    s.teamBattleAlternativeTeamsEnabled,
                    s.teamBattleAlternativeTeams,
                    s.teamBattleLeaders,
                    s.daysInAdvance,
                    s.msgMinutesBefore,
                    s.msgTemplate,
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
        minutesBefore: int,
        sendTime: int,
    ) -> None:
        with self.db as conn:
            conn.execute(
                "INSERT INTO scheduledMsgs (arenaId, scheduleId, team, template, minutesBefore, sendTime) VALUES (?, ?, ?, ?, ?, ?)",
                (arenaId, scheduleId, team, template, minutesBefore, sendTime),
            )

    def get_and_remove_scheduled_msgs(self) -> List[MsgToSend]:
        now = int(time())
        rows = self._query(
            "SELECT arenaId, team, template, sendTime FROM scheduledMsgs WHERE sendTime < ? AND sendTime > ?",
            (now, now - 30 * 60),
        )
        msgs = [
            MsgToSend(row["arenaId"], row["team"], row["template"], row["sendTime"])
            for row in rows
        ]
        with self.db as conn:
            conn.execute("DELETE FROM scheduledMsgs WHERE sendTime < ?", (now,))
        return msgs

    def update_scheduled_msgs(self, schedule: ScheduleWithId) -> None:
        with self.db as conn:
            self._begin()
            conn.execute(
                "DELETE FROM scheduledMsgs WHERE scheduleId = ?", (schedule.id,)
            )
            if (
                schedule.msgMinutesBefore
                and schedule.msgMinutesBefore > 0
                and schedule.msgTemplate
            ):
                conn.execute(
                    """INSERT INTO scheduledMsgs (arenaId, scheduleId, team, template, minutesBefore, sendTime) 
                        SELECT id, scheduleId, team, ?, ?, time - ? FROM createdArenas WHERE scheduleId = ?
                    """,
                    (
                        schedule.msgTemplate,
                        schedule.msgMinutesBefore,
                        schedule.msgMinutesBefore,
                        schedule.id,
                    ),
                )

    def update_scheduled_msg(
        self,
        arena: CreatedArena,
        minsBefore: Optional[int],
        template: Optional[str],
    ) -> None:
        with self.db as conn:
            self._begin()
            conn.execute("DELETE FROM scheduledMsgs WHERE arenaId = ?", (arena.id,))
            if minsBefore and minsBefore > 0 and template:
                conn.execute(
                    """INSERT INTO scheduledMsgs (arenaId, scheduleId, team, template, minutesBefore, sendTime)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        arena.id,
                        arena.scheduleId,
                        arena.team,
                        template,
                        minsBefore,
                        arena.time - minsBefore * 60,
                    ),
                )

    def scheduled_msg(self, arenaId: str) -> Optional[Tuple[int, str, str]]:
        row = self._query_one(
            "SELECT minutesBefore, template, team FROM scheduledMsgs WHERE arenaId = ?",
            (arenaId,),
        )
        if row:
            return (row["minutesBefore"], row["template"], row["team"])
        return None

    def set_token_for_team(self, team: str, token: str, user: str) -> None:
        with self.db as conn:
            conn.execute(
                "REPLACE INTO msgTokens (token, team, user, isBad, temporary) VALUES (?, ?, ?, false, false)",
                (token, team, user),
            )

    def token_for_team(self, team: str) -> Optional[str]:
        row = self._query_one(
            "SELECT token FROM msgTokens WHERE team = ? AND NOT isBad", (team,)
        )
        if row:
            return str(row["token"])
        return None

    def mark_bad_token(self, team: str, token: str) -> None:
        with self.db as conn:
            conn.execute(
                "UPDATE msgTokens SET isBad = true WHERE token = ? AND team = ?)",
                (token, team),
            )

    def token_state(self, team: str) -> dict:
        row = self._query_one(
            "SELECT user, isBad, temporary FROM msgTokens WHERE team = ?", (team,)
        )

        if not row:
            if self.team_needs_token(team):
                return {"issue": "missing"}
            return {}
        elif row["isBad"]:
            return {"issue": "bad"}
        elif row["temporary"]:
            return {"issue": "temporary"}

        return {"user": row["user"]}

    def team_needs_token(self, team: str) -> bool:
        result = self._query_one(
            "SELECT COUNT(*) FROM scheduledMsgs WHERE team = ?",
            (team,),
        )
        if result and int(result[0]) > 0:
            return True

        result = self._query_one(
            "SELECT COUNT(*) FROM schedules WHERE team = ? AND msgMinutesBefore IS NOT NULL AND msgMinutesBefore > 0 AND msgTemplate IS NOT NULL",
            (team,),
        )
        if result and int(result[0]) > 0:
            return True

        return False

    def token_user(self, team: str) -> Optional[str]:
        row = self._query_one(
            "SELECT user, isBad FROM msgTokens WHERE team = ?", (team,)
        )

        if row and not row["isBad"]:
            return str(row["user"])

        return None
