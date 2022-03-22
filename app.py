#!/usr/bin/env python3

from __future__ import annotations

import json
from typing import Any

from flask import Flask, abort, jsonify, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

import api
from auth import Auth
from db import Db, ParseError, Schedule, ScheduleWithId
from scheduler import SchedulerThread

OK_RESPONSE = '{"ok":true}'

app = Flask(__name__)
app.config.from_pyfile("config.py")

CORS(app)

api.HOST = app.config["HOST"]
Db.create_tables(app)
auth = Auth(app)
SchedulerThread(app.config["LICHESS_API_KEY"], app.logger).start()


@app.errorhandler(HTTPException)
def error_bad_request(e: Any) -> Any:
    response = e.get_response()
    response.data = json.dumps({
        "name": e.name,
        "description": e.description,
    })
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


@app.route("/create", methods=["POST"])
def create() -> str:
    try:
        j = request.json
        if not j:
            abort(400)
        schedule = Schedule.from_json(j)
    except ParseError as e:
        abort(400, description=str(e))

    auth().for_team(schedule.team)

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
    except ParseError as e:
        abort(400, description=str(e))

    auth().for_team(schedule.team)

    with Db() as db:
        db.update_schedule(schedule)
    
    return OK_RESPONSE


@app.route("/delete/<int:id>", methods=["POST"])
def delete(id: int) -> str:
    with Db() as db:
        team = db.team_of_schedule(id)
        if team is None:
            abort(404)
        auth().for_team(team)
        db.delete_schedule(id)

    return OK_RESPONSE

@app.route("/cancel/<id>", methods=["POST"])
def cancel(id: str) -> str:
    with Db() as db:
        team = db.team_of_created(id)
        if team is None:
            abort(404, description="This tournament either doesn't exist or wasn't created by the scheduler")
        auth().for_team(team)
        try:
            api.terminate_arena(id, app.config["LICHESS_API_KEY"])
        except Exception as e:
            app.logger.error(f"Failed to cancel tournament: {e}")
            abort(500, description="Failed to cancel tournament")

        db.delete_created(id)
        return OK_RESPONSE
