from __future__ import annotations

import json
from dataclasses import dataclass
from time import time
from typing import List, Optional, Set
import re

import requests

from db import Schedule
from model import ArenaEdit

HOST = "https://lichess.org"  # overridden from config in app.py
ENDPOINT_TEAMS = "/api/team/of/{}"
ENDPOINT_TOKEN_TEST = "/api/token/test"
ENDPOINT_TEAM_ARENAS = "/api/team/{}/arena"
ENDPOINT_CREATE_ARENA = "/api/tournament"
ENDPOINT_GET_ARENA = "/api/tournament/{}"
ENDPOINT_UPDATE_ARENA = "/api/tournament/{}"
ENDPOINT_TERMINATE_ARENA = "/api/tournament/{}/terminate"
ENDPOINT_TEAM_BATTLE = "/api/tournament/team-battle/{}"
BOOL = ["false", "true"]


@dataclass
class Token:
    userId: str
    expires: int
    scopes: List[str]


@dataclass(frozen=True)
class Arena:
    name: str
    time: int

    @staticmethod
    def from_json(s: dict) -> Arena:
        return Arena(s["fullName"], s["startsAt"] // 1000)


def verify_token(t: str) -> Optional[Token]:
    res = requests.post(HOST + ENDPOINT_TOKEN_TEST, data=t)
    res.raise_for_status()
    tt = res.json()[t]
    if not tt:
        return None
    return Token(tt["userId"], tt["expires"] // 1000, tt["scopes"].split(","))


def leader_teams(userId: str) -> List[str]:
    res = requests.get(HOST + ENDPOINT_TEAMS.format(userId))
    res.raise_for_status()
    teams = res.json()
    return [
        team["id"]
        for team in teams
        if any(userId == leader["id"] for leader in team["leaders"])
    ]


def future_team_arenas(teamId: str) -> Set[Arena]:
    res = requests.get(HOST + ENDPOINT_TEAM_ARENAS.format(teamId))
    res.raise_for_status()
    lines = res.text.splitlines()
    arenas = [Arena.from_json(json.loads(t)) for t in lines]
    now = time()
    return {a for a in arenas if a.time > now}


def schedule_arena(s: Schedule, at: int, api_key: str, prev: Optional[str]) -> str:
    data = {
        "name": s.name,
        "clockTime": s.clock,
        "clockIncrement": s.increment,
        "minutes": s.minutes,
        "startDate": at * 1000,
        "variant": s.variant,
        "rated": BOOL[s.rated],
        "berserkable": BOOL[s.berserkable],
        "streakable": BOOL[s.streakable],
    }
    if s.is_team_battle:
        data["teamBattleByTeam"] = s.team
    else:
        data["conditions.teamMember.teamId"] = s.team
    if s.position:
        data["position"] = s.position
    if s.description:
        desc = s.description
        if prev:
            desc.replace("](prev)", prev)
        else:
            desc = re.sub(r"\[.*?\]\(prev\)", "", desc)
        desc = desc.replace("](next)", "](soon)")
        data["description"] = desc
    if s.minRating:
        data["conditions.minRating.rating"] = s.minRating
    if s.maxRating:
        data["conditions.maxRating.rating"] = s.maxRating
    if s.minGames:
        data["conditions.nbRatedGames.nb"] = s.minGames

    resp = requests.post(
        HOST + ENDPOINT_CREATE_ARENA,
        headers={"Authorization": f"Bearer {api_key}"},
        data=data,
    )
    resp.raise_for_status()
    id = resp.json().get("id")
    if not isinstance(id, str):
        raise Exception(f"Created arena has invalid id: {id}")

    if s.is_team_battle:
        teams = s.team_battle_teams()
        leaders = s.teamBattleLeaders or 5
        resp = requests.post(
            HOST + ENDPOINT_TEAM_BATTLE.format(id),
            headers={"Authorization": f"Bearer {api_key}"},
            data={"teams": ",".join(teams), "nbLeaders": leaders},
        )
        resp.raise_for_status()

    return id


def update_team_battle(
    arena_id: str, teams: List[str], nbLeaders: Optional[int], api_key: str
) -> None:
    resp = requests.post(
        HOST + ENDPOINT_TEAM_BATTLE.format(arena_id),
        headers={"Authorization": f"Bearer {api_key}"},
        data={"teams": ",".join(teams), "nbLeaders": nbLeaders or 5},
    )
    resp.raise_for_status()


def terminate_arena(id: str, api_key: str) -> None:
    requests.post(
        HOST + ENDPOINT_TERMINATE_ARENA.format(id),
        headers={"Authorization": f"Bearer {api_key}"},
    ).raise_for_status()


def update_arena(arena: ArenaEdit, api_key: str) -> Optional[str]:
    data = {
        "name": arena.name,
        "clockTime": arena.clock,
        "clockIncrement": arena.increment,
        "minutes": arena.minutes,
        "variant": arena.variant,
        "rated": BOOL[arena.rated],
        "berserkable": BOOL[arena.berserkable],
        "streakable": BOOL[arena.streakable],
    }
    if arena.position:
        data["position"] = arena.position
    if arena.description:
        data["description"] = arena.description
    if arena.minRating:
        data["conditions.minRating.rating"] = arena.minRating
    if arena.maxRating:
        data["conditions.maxRating.rating"] = arena.maxRating
    if arena.minGames:
        data["conditions.nbRatedGames.nb"] = arena.minGames

    resp = requests.post(
        HOST + ENDPOINT_UPDATE_ARENA.format(arena.id),
        headers={"Authorization": f"Bearer {api_key}"},
        data=data,
    )

    if not resp.ok:
        return resp.text


def update_link_to_next_arena(id: str, nxt: str, api_key: str) -> None:
    resp = requests.get(HOST + ENDPOINT_GET_ARENA.format(id))
    resp.raise_for_status()
    arena = resp.json()
    desc = arena.get("description")
    if not desc or ("](soon)" not in desc and "](next)" not in desc):
        return

    data = {
        "clockTime": arena["clock"]["limit"] / 60,
        "clockIncrement": arena["clock"]["increment"],
        "minutes": arena["minutes"],
        "variant": arena["variant"],
        "description": desc.replace("](soon)", f"]({nxt})").replace(
            "](next)", f"]({nxt})"
        ),
    }
    if "minGames" in arena:
        data["conditions.nbRatedGames.nb"] = arena["minRatedGames"]["nb"]
    if "minRating" in arena:
        data["conditions.minRating.rating"] = arena["minRating"]["rating"]
    if "maxRating" in arena:
        data["conditions.maxRating.rating"] = arena["maxRating"]["rating"]

    requests.post(
        HOST + ENDPOINT_UPDATE_ARENA.format(id),
        headers={"Authorization": f"Bearer {api_key}"},
        data=data,
    ).raise_for_status()
