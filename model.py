from __future__ import annotations

import sqlite3
from calendar import timegm, monthrange
from dataclasses import dataclass
from datetime import datetime, timedelta
from time import time
from typing import Any, List, Optional
import re


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
    teamBattleTeams: Optional[str]
    teamBattleLeaders: Optional[int]
    daysInAdvance: Optional[int]

    @property
    def scheduleHour(self) -> int:
        return self.scheduleTime // 60

    @property
    def scheduleMinute(self) -> int:
        return self.scheduleTime % 60

    @property
    def is_team_battle(self) -> bool:
        return bool(self.teamBattleTeams)

    @property
    def days_in_advance(self) -> int:
        return self.daysInAdvance or 1

    def team_battle_teams(self) -> List[str]:
        return extract_team_battle_teams(self.team, self.teamBattleTeams)

    @staticmethod
    def from_json(j: dict) -> Schedule:
        scheduleDay = get_or_raise(j, "scheduleDay", int)
        scheduleStart = get_opt_or_raise(j, "scheduleStart", int)
        if scheduleDay < 0 or 7 < scheduleDay <= 1000 or scheduleDay >= 4000:
            raise ParseError(f"Invalid value for scheduleDay: {scheduleDay}")
        if scheduleDay > 1000:
            if scheduleDay % 1000 == 0:
                raise ParseError(f"Invalid value for scheduleDay: {scheduleDay}")
            if scheduleStart is None:
                raise ParseError("Missing scheduleStart for unregular period")
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
            scheduleDay,
            get_or_raise(j, "scheduleTime", int),
            scheduleStart,
            get_opt_or_raise(j, "scheduleEnd", int),
            get_opt_or_raise(j, "teamBattleTeams", str),
            get_opt_or_raise(j, "teamBattleLeaders", int),
            get_opt_or_raise(j, "daysInAdvance", int),
        )

    def next_times(self) -> List[int]:
        now = datetime.utcnow()
        new = now.replace(
            hour=self.scheduleHour,
            minute=self.scheduleMinute,
            second=0,
            microsecond=0,
        )
        delta: timedelta | int

        if self.scheduleDay == 0:
            delta = timedelta(days=1)
        elif self.scheduleDay < 8:
            new += timedelta(days=self.scheduleDay - now.isoweekday())
            delta = timedelta(days=7)
        else:
            if not self.scheduleStart:
                return []
            new = datetime.utcfromtimestamp(self.scheduleStart).replace(
                hour=self.scheduleHour,
                minute=self.scheduleMinute,
                second=0,
                microsecond=0,
            )
            unit = self.scheduleDay // 1000
            period = self.scheduleDay % 1000
            if period <= 0:
                return []
            if unit == 1:  # days
                delta = timedelta(days=period)
            elif unit == 2:  # weeks
                delta = timedelta(weeks=period)
            else:  # months
                delta = period

        while new < now:
            new = add_delta(new, delta)

        nxt = timegm(new.timetuple())

        endTime = int(time()) + self.days_in_advance * 24 * 60 * 60
        if self.scheduleEnd and self.scheduleEnd < endTime:
            endTime = self.scheduleEnd

        times = []
        while nxt <= endTime:
            if not self.scheduleStart or self.scheduleStart <= nxt:
                times.append(nxt)
                if len(times) == 5:
                    break
            new = add_delta(new, delta)
            nxt = timegm(new.timetuple())

        return times


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
            s.teamBattleTeams,
            s.teamBattleLeaders,
            s.daysInAdvance,
            get_or_raise(j, "id", int),
        )


@dataclass
class ArenaEdit:
    id: str
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
    isTeamBattle: bool
    teamBattleTeams: Optional[str]
    teamBattleLeaders: Optional[int]

    def team_battle_teams(self) -> List[str]:
        return extract_team_battle_teams(self.team, self.teamBattleTeams)

    @staticmethod
    def from_schedule(s: Schedule, id: str) -> ArenaEdit:
        return ArenaEdit(
            id,
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
            s.is_team_battle,
            s.teamBattleTeams,
            s.teamBattleLeaders,
        )

    @staticmethod
    def from_json(j: dict) -> ArenaEdit:
        return ArenaEdit(
            get_or_raise(j, "id", str),
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
            get_or_raise(j, "isTeamBattle", bool),
            get_opt_or_raise(j, "teamBattleTeams", str),
            get_opt_or_raise(j, "teamBattleLeaders", int),
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


def extract_team_battle_teams(team: str, ts: Optional[str]) -> List[str]:
    if not ts:
        return []
    teams = set(line.strip().split()[0] for line in ts.splitlines() if line.strip())
    teams.add(team)
    return [t for t in teams if re.match(r"^[\w-]{2,}$", t)]


def add_months(date: datetime, amnt: int) -> datetime:
    month = date.month - 1 + amnt
    year = date.year + month // 12
    month = month % 12 + 1
    day = min(date.day, monthrange(year, month)[1])
    return date.replace(year=year, month=month, day=day)


def add_delta(date: datetime, delta: timedelta | int) -> datetime:
    if isinstance(delta, int):
        return add_months(date, delta)
    else:
        return date + delta
