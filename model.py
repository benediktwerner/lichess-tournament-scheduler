from __future__ import annotations
import calendar

import re
import sqlite3
from calendar import monthrange
from dataclasses import dataclass
from datetime import datetime, timedelta
from time import time
from typing import Any, Dict, List, Optional, Protocol, Type, TypeVar

T = TypeVar("T")
U = TypeVar("U")


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
    minAccountAgeInDays: Optional[int]
    allowBots: bool
    scheduleDay: int
    scheduleTime: int
    scheduleStart: Optional[int]
    scheduleEnd: Optional[int]
    teamBattleTeams: Optional[str]
    teamBattleAlternativeTeamsEnabled: Optional[bool]
    teamBattleAlternativeTeams: Optional[str]
    teamBattleLeaders: Optional[int]
    daysInAdvance: Optional[int]
    msgMinutesBefore: Optional[int]
    msgTemplate: Optional[str]

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

    def team_battle_teams(self, at: int) -> List[str]:
        if self.teamBattleAlternativeTeamsEnabled:
            date = datetime.utcfromtimestamp(at)
            daysInMonth = calendar.monthrange(date.year, date.month)[1]
            if date.day > daysInMonth - 7:
                return extract_team_battle_teams(self.teamBattleAlternativeTeams)
        return extract_team_battle_teams(self.teamBattleTeams)

    @staticmethod
    def from_json(j: dict[str, Any]) -> Schedule:
        scheduleDay = get_or_raise(j, "scheduleDay", int)
        scheduleStart = get_opt_or_raise(j, "scheduleStart", int)
        if (
            scheduleDay < 0
            or 7 < scheduleDay <= 1000
            or 4000 <= scheduleDay < 10_000
            or 10_100 <= scheduleDay <= 20_000
            or 20_007 < scheduleDay
        ):
            raise ParseError(f"Invalid value for scheduleDay: {scheduleDay}")
        if 1000 < scheduleDay < 10_000:
            if scheduleDay % 1000 == 0:
                raise ParseError(f"Invalid value for scheduleDay: {scheduleDay}")
            if scheduleStart is None:
                raise ParseError("Missing scheduleStart for unregular period")
        elif 10_000 <= scheduleDay < 20_000:
            if scheduleDay % 10 > 6:
                raise ParseError(f"Invalid weekday: {scheduleDay % 10}")
            if scheduleDay % 100 // 10 > 4:
                raise ParseError(f"Invalid weekday ordinal: {scheduleDay}")
        name = get_or_raise(j, "name", str)
        long_name = re.sub(
            r"{weekOfMonth(?:\|(.*?))*}",
            lambda m: max(m.groups(), key=len, default="1"),
            re.sub(
                r"{n\+\d+}",
                "42",
                re.sub(
                    r"{nth\+\d+}",
                    "42nd",
                    name.replace("{n}", "42")
                    .replace("{nth}", "42nd")
                    .replace("{month}", "Jan."),
                ),
            ),
        )
        if len(long_name) > 30:
            raise ParseError("The tournament is longer than 30 characters")

        teamBattleTeams = get_opt_or_raise(j, "teamBattleTeams", str)
        if teamBattleTeams and not extract_team_battle_teams(teamBattleTeams):
            raise ParseError(
                "Invalid or empty team battle teams list. Expected one line per team starting with either the team ID or team page URL."
            )

        teamBattleAlternativeTeamsEnabled = get_opt_or_raise(
            j, "teamBattleAlternativeTeamsEnabled", bool
        )
        if teamBattleAlternativeTeamsEnabled:
            teamBattleAlternativeTeams = get_or_raise(
                j, "teamBattleAlternativeTeams", str
            )
            if not teamBattleAlternativeTeams or not extract_team_battle_teams(
                teamBattleAlternativeTeams
            ):
                raise ParseError(
                    "Invalid or empty team battle alternative teams list. Expected one line per team starting with either the team ID or team page URL."
                )
        else:
            teamBattleAlternativeTeams = None

        return Schedule(
            name,
            get_or_raise(j, "team", str),
            float(get_or_raise2(j, "clock", int, float)),
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
            get_opt_or_raise(j, "minAccountAgeInDays", int),
            get_or_raise(j, "allowBots", bool),
            scheduleDay,
            get_or_raise(j, "scheduleTime", int),
            scheduleStart,
            get_opt_or_raise(j, "scheduleEnd", int),
            teamBattleTeams,
            teamBattleAlternativeTeamsEnabled,
            teamBattleAlternativeTeams,
            get_opt_or_raise(j, "teamBattleLeaders", int),
            get_opt_or_raise(j, "daysInAdvance", int),
            get_opt_or_raise(j, "msgMinutesBefore", int),
            get_opt_or_raise(j, "msgTemplate", str),
        )

    def next_times(self) -> List[int]:
        now = datetime.utcnow()
        new = now.replace(
            hour=self.scheduleHour,
            minute=self.scheduleMinute,
            second=0,
            microsecond=0,
        )
        delta: NxtDateFinder

        if self.scheduleDay == 0:
            delta = AddDelta(timedelta(days=1))
        elif self.scheduleDay < 8:
            new += timedelta(days=self.scheduleDay - now.isoweekday())
            delta = AddDelta(timedelta(days=7))
        elif self.scheduleDay < 10_000:
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
                delta = AddDelta(timedelta(days=period))
            elif unit == 2:  # weeks
                delta = AddDelta(timedelta(weeks=period))
            else:  # months
                delta = AddMonths(period)
        elif self.scheduleDay < 20_000:
            weekday = self.scheduleDay % 10
            ordinal = self.scheduleDay % 100 // 10
            delta = XofMonth(weekday, ordinal)
            new = delta.in_month(new)
        else:
            day_to_skip = self.scheduleDay % 10
            if now.isoweekday() == day_to_skip:
                new += timedelta(days=1)
            delta = AddDayButSkipX(day_to_skip)

        while new < now:
            new = delta.find_next(new)

        nxt = int(new.timestamp())

        endTime = int(time()) + self.days_in_advance * 24 * 60 * 60
        if self.scheduleEnd and self.scheduleEnd < endTime:
            endTime = self.scheduleEnd

        times: List[int] = []
        while nxt <= endTime:
            if not self.scheduleStart or self.scheduleStart <= nxt:
                times.append(nxt)
                if len(times) == 5:
                    break
            new = delta.find_next(new)
            nxt = int(new.timestamp())

        return times


@dataclass
class ScheduleWithId(Schedule):
    id: int

    @staticmethod
    def from_row(row: sqlite3.Row) -> ScheduleWithId:
        s = ScheduleWithId(**row)  # type: ignore
        s.rated = bool(s.rated)
        s.berserkable = bool(s.berserkable)
        s.streakable = bool(s.streakable)
        s.allowBots = bool(s.allowBots)
        if s.teamBattleAlternativeTeamsEnabled is not None:
            s.teamBattleAlternativeTeamsEnabled = bool(
                s.teamBattleAlternativeTeamsEnabled
            )
        return s

    @staticmethod
    def from_json(j: Dict[str, object]) -> ScheduleWithId:
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
            s.minAccountAgeInDays,
            s.allowBots,
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
            get_or_raise(j, "id", int),
        )


@dataclass
class ArenaEdit:
    id: str
    name: str
    team: str
    startsAt: Optional[int]
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
    minAccountAgeInDays: Optional[int]
    allowBots: bool
    isTeamBattle: bool
    teamBattleTeams: Optional[str]
    teamBattleLeaders: Optional[int]
    msgMinutesBefore: Optional[int]
    msgTemplate: Optional[str]

    def team_battle_teams(self) -> List[str]:
        return extract_team_battle_teams(self.teamBattleTeams)

    @staticmethod
    def from_schedule(s: Schedule, id: str, at: int) -> ArenaEdit:
        return ArenaEdit(
            id,
            s.name,
            s.team,
            at,
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
            s.minAccountAgeInDays,
            s.allowBots,
            s.is_team_battle,
            s.teamBattleTeams,
            s.teamBattleLeaders,
            None,
            None,
        )

    @staticmethod
    def from_json(j: Dict[str, object]) -> ArenaEdit:
        return ArenaEdit(
            get_or_raise(j, "id", str),
            get_or_raise(j, "name", str),
            get_or_raise(j, "team", str),
            get_opt_or_raise(j, "startsAt", int),
            float(get_or_raise2(j, "clock", int, float)),
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
            get_opt_or_raise(j, "minAccountAgeInDays", int),
            get_or_raise(j, "allowBots", bool),
            get_or_raise(j, "isTeamBattle", bool),
            get_opt_or_raise(j, "teamBattleTeams", str),
            get_opt_or_raise(j, "teamBattleLeaders", int),
            get_opt_or_raise(j, "msgMinutesBefore", int),
            get_opt_or_raise(j, "msgTemplate", str),
        )


@dataclass
class CreatedArena:
    id: str
    scheduleId: int
    team: str
    time: int

    @staticmethod
    def from_row(row: sqlite3.Row) -> CreatedArena:
        return CreatedArena(**row)  # type: ignore


class ParseError(Exception):
    pass


def get_or_raise(j: Dict[str, object], key: str, typ: Type[T]) -> T:
    if key not in j:
        raise ParseError(f"Missing key: {key}")
    val = j[key]
    if isinstance(val, typ):
        return val
    raise ParseError(f"Invalid value for {key}: {val}")


def get_or_raise2(j: Dict[str, object], key: str, typ: Type[T], typ2: Type[U]) -> T | U:
    if key not in j:
        raise ParseError(f"Missing key: {key}")
    val = j[key]
    if isinstance(val, typ):
        return val
    if isinstance(val, typ2):
        return val
    raise ParseError(f"Invalid value for {key}: {val}")


def get_opt_or_raise(j: Dict[str, object], key: str, typ: Type[T]) -> T | None:
    val = j.get(key)
    if val is not None and not isinstance(val, typ):
        raise ParseError(f"Invalid value for {key}: {val}")
    return val


def extract_team_battle_teams(ts: Optional[str]) -> List[str]:
    if not ts:
        return []
    teams = set(line.strip().split()[0] for line in ts.splitlines() if line.strip())
    result: List[str] = []
    for team in teams:
        teamId = re.findall(r"^https://lichess.org/team/([\w-]{2,})$", team)
        if teamId:
            result.append(teamId[0])
        elif re.match(r"^[\w-]{2,}$", team):
            result.append(team)
    return result


def add_months(date: datetime, amnt: int) -> datetime:
    month = date.month - 1 + amnt
    year = date.year + month // 12
    month = month % 12 + 1
    day = min(date.day, monthrange(year, month)[1])
    return date.replace(year=year, month=month, day=day)


class NxtDateFinder(Protocol):
    def find_next(self, date: datetime) -> datetime:
        raise NotImplementedError


class AddDelta:
    def __init__(self, delta: timedelta):
        self.delta = delta

    def find_next(self, date: datetime) -> datetime:
        return date + self.delta


class AddMonths:
    def __init__(self, months: int):
        self.months = months

    def find_next(self, date: datetime) -> datetime:
        month = date.month - 1 + self.months
        year = date.year + month // 12
        month = month % 12 + 1
        day = min(date.day, monthrange(year, month)[1])
        return date.replace(year=year, month=month, day=day)


class XofMonth:
    def __init__(self, weekday: int, ordinal: int):
        self.weekday = weekday
        self.ordinal = ordinal

    def find_next(self, date: datetime) -> datetime:
        if date.month == 12:
            date = date.replace(year=date.year + 1, month=1)
        else:
            date = date.replace(month=date.month + 1)
        return self.in_month(date)

    def in_month(self, date: datetime) -> datetime:
        first, days = monthrange(date.year, date.month)
        if self.ordinal == 4:  # last
            last = (days + first - 1) % 7
            day = days - (last - self.weekday) % 7
        else:
            day = (self.weekday - first) % 7 + 1 + self.ordinal * 7
        return date.replace(day=day)


class AddDayButSkipX:
    def __init__(self, day_to_skip: int):
        self.day_to_skip = day_to_skip

    def find_next(self, date: datetime) -> datetime:
        new = date + timedelta(days=1)
        if new.isoweekday() == self.day_to_skip:
            new += timedelta(days=1)
        return new


@dataclass
class MsgToSend:
    arenaId: str
    team: str
    template: str
    sendTime: int

    def text(self) -> str:
        return self.template.replace(
            "{link}", f"https://lichess.org/tournament/{self.arenaId}"
        )
