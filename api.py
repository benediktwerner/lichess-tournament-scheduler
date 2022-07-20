from __future__ import annotations

import json
from dataclasses import dataclass
from time import time
from typing import List, Optional, Set
import re

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
    userId: str
    expires: int
    scopes: List[str]

    @property
    def allows_tournaments(self) -> bool:
        return "tournament:write" in self.scopes

    @property
    def allows_teams(self) -> bool:
        return "team:write" in self.scopes

    @property
    def expired(self) -> bool:
        return self.expires < time() - 24 * 60 * 60


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
            desc = desc.replace("](prev)", f"]({HOST + ARENA_URL.format(prev)})")
        else:
            desc = re.sub(r"\[.*?\]\(prev\)", "", desc)
        desc = re.sub(r"\[(.*?)\]\(next\)", "", r"\1")
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


def update_arena(
    arena: ArenaEdit, prev: Optional[str], nxt: Optional[str], api_key: str
) -> Optional[str]:
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
    if arena.startsAt:
        data["startDate"] = arena.startsAt * 1000
    if arena.position:
        data["position"] = arena.position
    if arena.description:
        desc = arena.description
        if prev:
            desc = desc.replace("](prev)", f"]({HOST + ARENA_URL.format(prev)})")
        else:
            desc = re.sub(r"\[.*?\]\(prev\)", "", desc)
        if nxt:
            nxt_url = HOST + ARENA_URL.format(nxt)
            desc = desc.replace("](next)", f"]({nxt_url})")
        else:
            desc = re.sub(r"\[(.*?)\]\(next\)", "", r"\1")
        data["description"] = desc
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


def update_link_to_next_arena(
    id: str, prev: Optional[str], nxt: str, desc: str, api_key: str
) -> None:
    resp = requests.get(HOST + ENDPOINT_GET_ARENA.format(id))
    resp.raise_for_status()
    arena = resp.json()

    if prev:
        desc = desc.replace("](prev)", f"]({HOST + ARENA_URL.format(prev)})")
    else:
        desc = re.sub(r"\[.*?\]\(prev\)", "", desc)
    desc = desc.replace("](next)", f"]({HOST + ARENA_URL.format(nxt)})")

    data = {
        "clockTime": arena["clock"]["limit"] / 60,
        "clockIncrement": arena["clock"]["increment"],
        "minutes": arena["minutes"],
        "variant": arena["variant"],
        "description": desc,
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


def send_team_msg(msg: MsgToSend) -> None:
    requests.post(
        HOST + ENDPOINT_TEAM_PM.format(msg.team),
        headers={"Authorization": f"Bearer {msg.token}"},
        data={"message": msg.text()},
    ).raise_for_status()
