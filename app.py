#!/usr/bin/env python3

from __future__ import annotations

import json
import logging
from collections import defaultdict
from time import time
from typing import Any, DefaultDict, Dict, List, cast

from flask import Flask, abort, jsonify, request
from flask.logging import default_handler  # pyright: ignore
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

import api
from auth import Auth
from db import Db
from model import ArenaEdit, ParseError, Schedule, ScheduleWithId, get_or_raise
from scheduler import SchedulerThread, SchedulerWatchdog

OK_RESPONSE = '{"ok":true}'
API_VERSION = "6"

root = logging.getLogger()
root.addHandler(default_handler)  # pyright: ignore

app = Flask(__name__)
app.config.from_pyfile("config.py")
app.logger.setLevel(logging.INFO)

LICHESS_API_KEY = cast(str, app.config["LICHESS_API_KEY"])
TEAMS_WHITELIST = cast(List[str], app.config["TEAMS_WHITELIST"])
ADMINS = cast(List[str], app.config["ADMINS"])

try:
    CORS(app)
    api.HOST = app.config["HOST"]

    # don't leak db into global scope
    def create_tables() -> None:
        with Db() as db:
            db.create_tables(app)

    create_tables()

    auth = Auth(ADMINS, TEAMS_WHITELIST)
    SchedulerThread(LICHESS_API_KEY).start()
    SchedulerWatchdog().start()

except Exception as e:
    app.logger.error(f"Exception during startup: {e}")
    raise e


@app.errorhandler(HTTPException)
def error_bad_request(e: Any) -> Any:
    response = e.get_response()
    response.data = json.dumps(
        {
            "name": e.name,
            "description": e.description,
        }
    )
    response.content_type = "application/json"
    return response


@app.route("/version")
def version() -> str:
    return API_VERSION


@app.route("/schedules")
def schedules() -> Any:
    user = auth()
    with Db() as db:
        by_team: DefaultDict[str, List[ScheduleWithId]] = defaultdict(list)
        for s in db.schedules():
            by_team[s.team].append(s)
        teams = TEAMS_WHITELIST if user.is_admin else user.teams
        return jsonify([(team, by_team[team]) for team in teams])


@app.route("/scheduledMsg/<id>")
def scheduledMsg(id: str) -> Any:
    user = auth()
    with Db() as db:
        msg = db.scheduled_msg(id)
    if not msg:
        return jsonify({})
    minsBefore, template, team = msg
    user.assert_for_team(team)
    return jsonify({"msgMinutesBefore": minsBefore, "msgTemplate": template})


@app.route("/tokenState")
def tokenState() -> Any:
    user = auth()
    state = {}
    teams = TEAMS_WHITELIST if user.is_admin else user.teams
    with Db() as db:
        for team in teams:
            state[team] = db.token_state(team)
    return jsonify(state)


@app.route("/tokenUser/<team>")
def tokenExists(team: str) -> Any:
    user = auth()
    user.assert_for_team(team)
    with Db() as db:
        return jsonify({"user": db.token_user(team)})


@app.route("/setToken/<team>", methods=["POST"])
def setToken(team: str) -> Any:
    user = auth()
    user.assert_for_team(team)

    j = request.json
    if not j or not isinstance(j, dict):
        abort(400, description="Invalid request body")

    token = cast(Dict[str, object], j).get("token")
    if not token or not isinstance(token, str):
        abort(400, desciption="Missing or invalid token")

    vToken = api.verify_token(token)

    if not vToken or not vToken.is_valid_msg_token_for_team(team):
        abort(400, description="Invalid token")

    with Db() as db:
        db.set_token_for_team(team, token, vToken.userId)

    return OK_RESPONSE


@app.route("/createdUpcomingIds")
def createdUpcomingIds() -> Any:
    auth()
    by_team: DefaultDict[str, List[str]] = defaultdict(list)
    with Db() as db:
        for id, team in db.created_upcoming():
            by_team[team].append(id)
    return jsonify(by_team)


@app.route("/create", methods=["POST"])
def create() -> str:
    user = auth()

    try:
        j = request.json
        if not j:
            abort(400)
        schedule = Schedule.from_json(j)
    except ParseError as e:
        abort(400, description=str(e))

    user.assert_for_team(schedule.team)

    with Db() as db:
        db.insert_schedule(schedule)

    return OK_RESPONSE


@app.route("/edit", methods=["POST"])
def edit() -> str:
    user = auth()

    try:
        j = request.json
        if not j:
            abort(400)
        schedule = ScheduleWithId.from_json(j)
        update_created = get_or_raise(j, "updateCreated", bool)
    except ParseError as e:
        abort(400, description=str(e))

    user.assert_for_team(schedule.team)

    with Db() as db:
        db.update_schedule(schedule)

        if not update_created:
            return OK_RESPONSE

        db.update_scheduled_msgs(schedule)

        upcoming = db.created_upcoming_with_schedule(schedule.id)
        prev = db.previous_created(schedule.id, int(time()))
        nth = db.num_created_before(schedule.id, int(time()))

        for i, (id, at) in enumerate(upcoming):
            err = api.update_arena(
                ArenaEdit.from_schedule(schedule, id, at),
                upcoming[i - 1][0] if i > 0 else prev,
                upcoming[i + 1][0] if i + 1 < len(upcoming) else None,
                nth + i + 1,
                LICHESS_API_KEY,
            )
            if err is not None:
                abort(500, description=f"Failed to update tournament {id}: {err}")

            if schedule.is_team_battle:
                try:
                    api.update_team_battle(
                        id,
                        schedule.team_battle_teams(at),
                        schedule.teamBattleLeaders,
                        LICHESS_API_KEY,
                    )
                except Exception as e:
                    app.logger.error(f"Failed to update arena teams: {e}")
                    abort(
                        500,
                        description=f"Failed to update teams for {id}",
                    )

    return OK_RESPONSE


@app.route("/editArena", methods=["POST"])
def editArena() -> str:
    user = auth()
    try:
        j = request.json
        if not j:
            abort(400)
        arena = ArenaEdit.from_json(j)
    except ParseError as e:
        abort(400, description=str(e))

    user.assert_for_team(arena.team)

    with Db() as db:
        old = db.created(arena.id)
        if old is None or old.team != arena.team:
            abort(
                404,
                description="This tournament either doesn't exist or wasn't created by the scheduler",
            )

    err = api.update_arena(arena, None, None, 0, LICHESS_API_KEY)
    if err is not None:
        abort(500, description=f"Failed to edit tournament: {err}")

    with Db() as db:
        if arena.startsAt:
            old.time = arena.startsAt
        db.update_created(old)
        db.update_scheduled_msg(old, arena.msgMinutesBefore, arena.msgTemplate)

    if arena.isTeamBattle:
        try:
            api.update_team_battle(
                arena.id,
                arena.team_battle_teams(),
                arena.teamBattleLeaders,
                LICHESS_API_KEY,
            )
        except Exception as e:
            app.logger.error(f"Failed to update arena teams: {e}")
            abort(
                500,
                description="Failed to update team battle teams (but other changes were applied successfully)",
            )

    return OK_RESPONSE


@app.route("/delete/<int:id>", methods=["POST"])
def delete(id: int) -> str:
    with Db() as db:
        team = db.team_of_schedule(id)
        if team is None:
            abort(404)
        auth().assert_for_team(team)
        db.delete_schedule(id)

    return OK_RESPONSE


@app.route("/cancel/<id>", methods=["POST"])
def cancel(id: str) -> str:
    with Db() as db:
        arena = db.created(id)
        if arena is None:
            abort(
                404,
                description="This tournament either doesn't exist or wasn't created by the scheduler",
            )
        auth().assert_for_team(arena.team)
        try:
            api.terminate_arena(id, LICHESS_API_KEY)
        except Exception as e:
            app.logger.error(f"Failed to cancel tournament: {e}")
            abort(500, description="Failed to cancel tournament")

        db.delete_created(id)
        return OK_RESPONSE
