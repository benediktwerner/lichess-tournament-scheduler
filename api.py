from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import datetime
from time import time
from typing import List, Optional, Tuple, cast

import dateutil.parser
import requests

from db import Schedule
from model import ArenaEdit, MsgToSend

HOST = "https://lichess.org"  # overridden from config in app.py
ARENA_URL = "/tournament/{}"
ENDPOINT_TEAMS = "/api/team/of/{}"
ENDPOINT_TOKEN_TEST = "/api/token/test"
ENDPOINT_TEAM_ARENAS = "/api/team/{}/arena"
ENDPOINT_CREATE_ARENA = "/api/tournament"
ENDPOINT_GET_ARENA = "/api/tournament/{}"
ENDPOINT_UPDATE_ARENA = "/api/tournament/{}"
ENDPOINT_TERMINATE_ARENA = "/api/tournament/{}/terminate"
ENDPOINT_TEAM_BATTLE = "/api/tournament/team-battle/{}"
ENDPOINT_TEAM_PM = "/team/{}/pm-all"
BOOL = ["false", "true"]


@dataclass
class Token:
    token: str
    userId: str
    expires: Optional[int]
    scopes: List[str]

    @property
    def allows_tournaments(self) -> bool:
        return "tournament:write" in self.scopes

    @property
    def allows_teams(self) -> bool:
        return "team:lead" in self.scopes

    @property
    def expired(self) -> bool:
        return self.expires is not None and self.expires < time() - 24 * 60 * 60

    def is_valid_msg_token_for_team(self, team: str) -> bool:
        return (
            not self.expired
            and self.allows_teams
            and team in leader_teams(self.userId, self.token)
        )


def verify_token(t: str) -> Optional[Token]:
    res = requests.post(HOST + ENDPOINT_TOKEN_TEST, data=t)
    res.raise_for_status()
    tt = res.json()[t]
    if not tt:
        return None
    expires = tt.get("expires")
    if expires is not None:
        expires //= 1000
    return Token(t, tt["userId"], expires, tt["scopes"].split(","))


def leader_teams(userId: str, token: str) -> List[str]:
    res = requests.get(
        HOST + ENDPOINT_TEAMS.format(userId),
        headers={"Authorization": f"Bearer {token}"},
    )
    res.raise_for_status()
    teams = res.json()
    return [
        team["id"]
        for team in teams
        if any(userId == leader["id"] for leader in team["leaders"])
    ]


def schedule_arena(
    s: Schedule, at: int, api_key: str, nth: int, prev: Optional[str]
) -> Tuple[str, Optional[str]]:
    name = format_name(s.name, at, nth)
    data = {
        "name": name,
        "clockTime": s.clock,
        "clockIncrement": s.increment,
        "minutes": s.minutes,
        "startDate": at * 1000,
        "variant": s.variant,
        "rated": BOOL[s.rated],
        "berserkable": BOOL[s.berserkable],
        "streakable": BOOL[s.streakable],
        "conditions.bots": BOOL[s.allowBots],
    }
    if s.is_team_battle:
        data["teamBattleByTeam"] = s.team
    else:
        data["conditions.teamMember.teamId"] = s.team
    if s.position:
        data["position"] = s.position
    if s.description:
        data["description"] = format_description(
            s.description, prev, None, name, at, nth
        )
    if s.minRating:
        data["conditions.minRating.rating"] = s.minRating
    if s.maxRating:
        data["conditions.maxRating.rating"] = s.maxRating
    if s.minGames:
        data["conditions.nbRatedGame.nb"] = s.minGames
    if s.minAccountAgeInDays:
        data["conditions.accountAge"] = s.minAccountAgeInDays

    resp = requests.post(
        HOST + ENDPOINT_CREATE_ARENA,
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        data=data,
    )
    resp.raise_for_status()
    json = resp.json()
    id = json.get("id")
    if not isinstance(id, str):
        raise Exception(f"Created arena has invalid id: {id}")

    if s.is_team_battle:
        teams = s.team_battle_teams(at)
        leaders = s.teamBattleLeaders or 5
        resp = requests.post(
            HOST + ENDPOINT_TEAM_BATTLE.format(id),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            },
            data={"teams": ",".join(teams), "nbLeaders": leaders},
        )
        resp.raise_for_status()

    return id, json.get("fullName")


def update_team_battle(
    arena_id: str, teams: List[str], nbLeaders: Optional[int], api_key: str
) -> None:
    resp = requests.post(
        HOST + ENDPOINT_TEAM_BATTLE.format(arena_id),
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        data={"teams": ",".join(teams), "nbLeaders": nbLeaders or 5},
    )
    resp.raise_for_status()


def terminate_arena(id: str, api_key: str) -> None:
    requests.post(
        HOST + ENDPOINT_TERMINATE_ARENA.format(id),
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
    ).raise_for_status()


def update_arena(
    arena: ArenaEdit, prev: Optional[str], nxt: Optional[str], nth: int, api_key: str
) -> Optional[str]:
    at = arena.startsAt or 0
    name = format_name(arena.name, at, nth)
    data = {
        "name": name,
        "clockTime": arena.clock,
        "clockIncrement": arena.increment,
        "minutes": arena.minutes,
        "variant": arena.variant,
        "rated": BOOL[arena.rated],
        "berserkable": BOOL[arena.berserkable],
        "streakable": BOOL[arena.streakable],
        "conditions.bots": BOOL[arena.allowBots],
    }
    if arena.startsAt:
        data["startDate"] = arena.startsAt * 1000
    if arena.position:
        data["position"] = arena.position
    if arena.description:
        data["description"] = format_description(
            arena.description, prev, nxt, name, at, nth
        )
    if arena.minRating:
        data["conditions.minRating.rating"] = arena.minRating
    if arena.maxRating:
        data["conditions.maxRating.rating"] = arena.maxRating
    if arena.minGames:
        data["conditions.nbRatedGame.nb"] = arena.minGames
    if arena.minAccountAgeInDays:
        data["conditions.accountAge"] = arena.minAccountAgeInDays

    resp = requests.post(
        HOST + ENDPOINT_UPDATE_ARENA.format(arena.id),
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        data=data,
    )

    if not resp.ok:
        return str(resp.text)

    return None


def update_link_to_next_arena(
    id: str, prev: Optional[str], nxt: str, desc: str, nth: int, api_key: str
) -> None:
    resp = requests.get(HOST + ENDPOINT_GET_ARENA.format(id))
    resp.raise_for_status()
    arena = resp.json()

    name = arena["fullName"]
    if name.endswith(" Arena"):
        name = name[: -len(" Arena")]
    elif name.endswith(" Team Battle"):
        name = name[: -len(" Team Battle")]
    at = int(dateutil.parser.isoparse(arena["startsAt"]).timestamp())

    data = {
        "clockTime": arena["clock"]["limit"] / 60,
        "clockIncrement": arena["clock"]["increment"],
        "minutes": arena["minutes"],
        "variant": arena["variant"],
        "description": format_description(desc, prev, nxt, name, at, nth),
    }
    if "minGames" in arena:
        data["conditions.nbRatedGame.nb"] = arena["minRatedGames"]["nb"]
    if "minRating" in arena:
        data["conditions.minRating.rating"] = arena["minRating"]["rating"]
    if "maxRating" in arena:
        data["conditions.maxRating.rating"] = arena["maxRating"]["rating"]
    if "botsAllowed" in arena:
        data["conditions.bots"] = arena["botsAllowed"]
    if "minAccountAgeInDays" in arena:
        data["conditions.accountAge"] = arena["minAccountAgeInDays"]

    requests.post(
        HOST + ENDPOINT_UPDATE_ARENA.format(id),
        headers={"Authorization": f"Bearer {api_key}", "Accept": "application/json"},
        data=data,
    ).raise_for_status()


def send_team_msg(msg: MsgToSend, token: str) -> None:
    requests.post(
        HOST + ENDPOINT_TEAM_PM.format(msg.team),
        headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
        data={"message": msg.text()},
    ).raise_for_status()


def replace_week_of_month(s: str, date: datetime) -> str:
    def f(m: re.Match[str]) -> str:
        week = (date.day - 1) // 7
        groups = cast(Tuple[str, ...], m.groups())
        if groups:
            daysInMonth = calendar.monthrange(date.year, date.month)[1]
            if date.day > daysInMonth - 7:
                return groups[-1]
            if len(groups) == 5:
                return groups[week]
        return str(week + 1)

    return re.sub(r"{weekOfMonth(?:\|(.*?))*}", f, s)


def format_name(name: str, at: int, nth: int) -> str:
    date = datetime.utcfromtimestamp(at)
    name = name.replace("{n}", str(nth))
    name = name.replace("{nth}", format_nth(nth))
    name = re.sub(r"{n\+(\d+)}", lambda m: str(nth + int(m.group(1))), name)
    name = re.sub(r"{nth\+(\d+)}", lambda m: format_nth(nth + int(m.group(1))), name)
    name = replace_week_of_month(name, date)
    name_long = name.replace("{month}", f"{date:%B}")
    if len(name_long) <= 30:
        return name_long
    return name.replace("{month}", f"{date:%b}.")


def format_description(
    desc: str, prev: Optional[str], nxt: Optional[str], name: str, at: int, nth: int
) -> str:
    if prev:
        desc = desc.replace("](prev)", f"]({HOST + ARENA_URL.format(prev)})")
    else:
        desc = re.sub(r"\[[^\n\[\]]+\]\(prev\)", "", desc)
    if nxt:
        desc = desc.replace("](next)", f"]({HOST + ARENA_URL.format(nxt)})")
    else:
        desc = re.sub(r"\[([^\n\[\]]+)\]\(next\)", r"\1", desc)
    date = datetime.utcfromtimestamp(at)
    desc = desc.replace("{month}", f"{date:%B}")
    desc = desc.replace("{n}", str(nth))
    desc = desc.replace("{nth}", format_nth(nth))
    desc = re.sub(r"{n\+(\d+)}", lambda m: str(nth + int(m.group(1))), desc)
    desc = re.sub(r"{nth\+(\d+)}", lambda m: format_nth(nth + int(m.group(1))), desc)
    desc = replace_week_of_month(desc, date)
    desc = desc.replace("{name}", name)
    return desc


def format_nth(n: int) -> str:
    if (n % 100) // 10 == 1:
        return f"{n}th"
    m = n % 10
    if m == 1:
        return f"{n}st"
    if m == 2:
        return f"{n}nd"
    if m == 3:
        return f"{n}rd"
    return f"{n}th"
