from __future__ import annotations

import json
from dataclasses import dataclass
from time import time
from typing import List, Optional, Set

import requests

from db import Schedule

HOST = "https://lichess.org"
ENDPOINT_TEAMS = "/api/team/of/{}"
ENDPOINT_TOKEN_TEST = "/api/token/test"
ENDPOINT_TEAM_ARENAS = "/api/team/{}/arena"
ENDPOINT_CREATE_ARENA = "/api/tournament"
ENDPOINT_TERMINATE_ARENA = "/api/tournament/{}/terminate"
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
    return Token(tt["userId"], tt["expires"], tt["scopes"].split(","))


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


def schedule_arena(s: Schedule, at: int, api_key: str) -> str:
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
        "conditions.teamMember.teamId": s.team,
    }
    if s.position:
        data["position"] = s.position
    if s.description:
        data["description"] = s.description
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
    return id


def terminate_arena(id: str, api_key: str) -> None:
    requests.post(
        HOST + ENDPOINT_TERMINATE_ARENA.format(id),
        headers={"Authorization": f"Bearer {api_key}"},
    ).raise_for_status()
