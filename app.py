#!/usr/bin/env python3

from __future__ import annotations

import json
import logging
from typing import Any
from datetime import datetime
from time import time

from flask import Flask, abort, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

import api
from auth import Auth
from db import Db
from model import ArenaEdit, ParseError, Schedule, ScheduleWithId, get_or_raise
from scheduler import SchedulerThread

OK_RESPONSE = '{"ok":true}'

app = Flask(__name__)
app.config.from_pyfile("config.py")
app.logger.setLevel(logging.INFO)

try:
    CORS(app)
    api.HOST = app.config["HOST"]

    # don't leak db into global scope
    def create_tables() -> None:
        with Db() as db:
            db.create_tables(app)
    create_tables()

    auth = Auth(app)
    SchedulerThread(app.config["LICHESS_API_KEY"], app.logger).start()

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


@app.route("/schedules")
def schedules() -> Any:
    user = auth()
    with Db() as db:
        by_team = {team: [] for team in app.config["TEAMS_WHITELIST"]}
        for s in db.schedules():
            by_team[s.team].append(s)
        teams = app.config["TEAMS_WHITELIST"] if user.is_admin else user.teams
        return jsonify([(team, by_team[team]) for team in teams])


@app.route("/createdUpcomingIds")
def createdUpcomingIds() -> Any:
    auth()
    with Db() as db:
        return jsonify(db.created_upcoming_ids())


@app.route("/create", methods=["POST"])
def create() -> str:
    try:
        j = request.json
        if not j:
            abort(400)
        schedule = Schedule.from_json(j)
    except ParseError as e:
        abort(400, description=str(e))

    auth().assert_for_team(schedule.team)

    with Db() as db:
        db.insert_schedule(schedule)

    return OK_RESPONSE


@app.route("/edit", methods=["POST"])
def edit() -> str:
    try:
        j = request.json
        if not j:
            abort(400)
        schedule = ScheduleWithId.from_json(j)
        update_created = get_or_raise(j, "updateCreated", bool)
    except ParseError as e:
        abort(400, description=str(e))

    auth().assert_for_team(schedule.team)

    with Db() as db:
        db.update_schedule(schedule)

        if not update_created:
            return OK_RESPONSE

        teams = schedule.team_battle_teams()
        leaders = schedule.teamBattleLeaders
        upcoming = db.created_upcoming_with_schedule(schedule.id)
        prev = db.previous_created(schedule.id, int(time()))

        for i, id in enumerate(upcoming):
            err = api.update_arena(
                ArenaEdit.from_schedule(schedule, id),
                upcoming[i - 1] if i > 0 else prev,
                upcoming[i + 1] if i + 1 < len(upcoming) else None,
                app.config["LICHESS_API_KEY"],
            )
            if err is not None:
                abort(500, f"Failed to update tournament {id}: {err}")

            if schedule.is_team_battle:
                try:
                    api.update_team_battle(
                        id, teams, leaders, app.config["LICHESS_API_KEY"]
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
    try:
        j = request.json
        if not j:
            abort(400)
        arena = ArenaEdit.from_json(j)
    except ParseError as e:
        abort(400, description=str(e))

    auth().assert_for_team(arena.team)

    team = db.team_of_created(arena.id)
    if team is None or team != arena.team:
        abort(
            404,
            description="This tournament either doesn't exist or wasn't created by the scheduler",
        )

    err = api.update_arena(arena, app.config["LICHESS_API_KEY"])
    if err is not None:
        abort(500, description=f"Failed to edit tournament: {err}")

    if arena.isTeamBattle:
        try:
            api.update_team_battle(
                arena.id,
                arena.team_battle_teams(),
                arena.teamBattleLeaders,
                app.config["LICHESS_API_KEY"],
            )
        except Exception as e:
            app.logger.error(f"Failed to update arena teams: {e}")
            abort(
                500,
                description="Failed to update teams (but other changes were applied successfully)",
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
        team = db.team_of_created(id)
        if team is None:
            abort(
                404,
                description="This tournament either doesn't exist or wasn't created by the scheduler",
            )
        auth().assert_for_team(team)
        try:
            api.terminate_arena(id, app.config["LICHESS_API_KEY"])
        except Exception as e:
            app.logger.error(f"Failed to cancel tournament: {e}")
            abort(500, description="Failed to cancel tournament")

        db.delete_created(id)
        return OK_RESPONSE


@app.route("/logs", methods=["GET"])
def logs() -> str:
    auth().assert_admin()

    with Db() as db:
        logs = db.logs()

    return "\n".join(
        f"[{datetime.utcfromtimestamp(time / 1_000_000):%Y-%m-%d %H:%M:%S %f}] {text}"
        for time, text in logs
    )
