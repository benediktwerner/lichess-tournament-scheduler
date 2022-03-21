#!/usr/bin/env python3

from __future__ import annotations
from typing import Any

from flask import Flask, abort, jsonify, request

from auth import Auth
from scheduler import SchedulerThread
from db import Db, ParseError, Schedule, ScheduleWithId

app = Flask(__name__)
app.config.from_pyfile("config.py")

Db.create_tables()

auth = Auth()

SchedulerThread(app.config["LICHESS_API_KEY"]).start()


@app.errorhandler(400)
def error_bad_request(e: Any) -> Any:
    return jsonify(error=str(e)), 400


@app.route("/schedules")
def schedules() -> Any:
    with Db() as db:
        return jsonify(db.schedules())


@app.route("/create", methods=["POST"])
def create() -> None:
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


@app.route("/edit", methods=["POST"])
def edit() -> None:
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


@app.route("/delete/<int:id>", methods=["POST"])
def delete(id: int) -> None:
    with Db() as db:
        team = db.team_of_schedule(id)
        if team is None:
            abort(404)
        auth().for_team(team)
        db.delete_schedule(id)
