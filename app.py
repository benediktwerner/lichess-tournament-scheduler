#!/usr/bin/env python3

from collections import defaultdict

from flask import Flask, redirect, render_template, g, request, url_for, abort
from flask_wtf import CSRFProtect
import sqlite3

app = Flask(__name__)
app.config.from_pyfile("config.py")
CSRFProtect(app)

DATABASE = "database.sqlite"

VARIANTS = [
    ("standard", "Standard"),
    ("chess960", "Chess 960"),
    ("crazyhouse", "Crazyhouse"),
    ("antichess", "Antichess"),
    ("atomic", "Atomic"),
    ("horde", "Horde"),
    ("kingOfTheHill", "King Of The Hill"),
    ("racingKings", "Racing Kings"),
    ("threeCheck", "Three Check"),
]
VARIANTS_MAP = dict(VARIANTS)

TEAMS_WHITELIST = [
    "lichess-antichess",
    "lichess-chess960",
    "lichess-king-of-the-hill",
    "lichess-three-check",
    "lichess-atomic",
    "lichess-horde",
    "lichess-racing-kings",
    "lichess-crazyhouse",
]
TEAM_TO_VARIANT = {
    "lichess-antichess": "antichess",
    "lichess-chess960": "chess960",
    "lichess-king-of-the-hill": "kingOfTheHill",
    "lichess-three-check": "threeCheck",
    "lichess-atomic": "atomic",
    "lichess-horde": "horde",
    "lichess-racing-kings": "racingKings",
    "lichess-crazyhouse": "crazyhouse",
}

SCHEDULES = [
    "Every day",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
]


def get_db():
    db = getattr(g, "_database", None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db


def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    cur.close()
    return (rv[0] if rv else None) if one else rv


def insert_db(table, values):
    keys = ",".join(k for k, _ in values)
    values = [v for _, v in values]

    db = get_db()
    db.cursor().execute(
        f"INSERT INTO {table} ({keys}) VALUES ({','.join('?' * len(values))})", values
    )
    db.commit()


def update_db(table, id, values):
    keys = ",".join(f"{k} = ?" for k, _ in values)
    values = [v for _, v in values]
    values.append(id)

    db = get_db()
    db.cursor().execute(f"UPDATE {table} SET {keys} WHERE id = ?", values)
    db.commit()


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, "_database", None)
    if db is not None:
        db.close()


@app.route("/")
def index():
    schedules = query_db("SELECT * FROM schedules")
    by_teams = {team: [] for team in ["lichess-horde"]}
    for schedule in schedules:
        by_teams[schedule["team"]].append(schedule)
    return render_template(
        "index.html", teams=by_teams, variants=VARIANTS_MAP, schedule_names=SCHEDULES
    )


@app.route("/create/<team>", methods=["GET", "POST"])
def create(team):
    if request.method == "POST":
        values = [("team", team)]

        for key in [
            "scheduleDay",
            "name",
            "clock",
            "increment",
            "minutes",
        ]:
            values.append((key, request.form[key]))
        for key in [
            "rated",
            "berserkable",
            "streakable",
        ]:
            values.append((key, request.form.get(key, False)))

        scheduleTime = request.form["scheduleTime"]
        hh, mm = scheduleTime.split(":")
        scheduleTime = int(hh) * 60 + int(mm)
        values.append(("scheduleTime", scheduleTime))

        def add_if(key, cond=None):
            val = request.form.get(key)
            if val and (cond is None or cond(val)):
                values.append((key, val))

        add_if("variant", lambda v: v and v != "standard")
        add_if("position", str.strip)
        add_if("description", str.strip)
        add_if(
            "minRating", lambda x: request.form.get("minRating-enabled") and int(x) > 0
        )
        add_if(
            "maxRating", lambda x: request.form.get("maxRating-enabled") and int(x) > 0
        )
        add_if(
            "minGames", lambda x: request.form.get("minGames-enabled") and int(x) > 0
        )

        insert_db("schedules", values)

        return redirect(url_for("index"))
    else:
        return render_template(
            "edit.html",
            type="create",
            schedule=defaultdict(
                lambda: "",
                {"team": team, "variant": TEAM_TO_VARIANT.get(team, "standard")},
            ),
            variants=VARIANTS,
            schedules=SCHEDULES,
        )


@app.route("/edit/<id>", methods=["GET", "POST"])
def edit(id):
    if request.method == "POST":
        values = []

        for key in [
            "scheduleDay",
            "name",
            "clock",
            "increment",
            "minutes",
        ]:
            values.append((key, request.form[key]))
        for key in [
            "rated",
            "berserkable",
            "streakable",
        ]:
            values.append((key, request.form.get(key, False)))

        scheduleTime = request.form["scheduleTime"]
        hh, mm = scheduleTime.split(":")
        scheduleTime = int(hh) * 60 + int(mm)
        values.append(("scheduleTime", scheduleTime))

        def add_if(key, cond=None):
            val = request.form.get(key)
            if val and (cond is None or cond(val)):
                values.append((key, val))
            else:
                values.append((key, None))

        add_if("variant", lambda v: v and v != "standard")
        add_if("position", str.strip)
        add_if("description", str.strip)
        add_if(
            "minRating", lambda x: request.form.get("minRating-enabled") and int(x) > 0
        )
        add_if(
            "maxRating", lambda x: request.form.get("maxRating-enabled") and int(x) > 0
        )
        add_if(
            "minGames", lambda x: request.form.get("minGames-enabled") and int(x) > 0
        )

        update_db("schedules", id, values)

        return redirect(url_for("index"))
    else:
        schedule = query_db("SELECT * FROM schedules WHERE id = ?", id, one=True)
        if schedule is None:
            abort(404)
        return render_template(
            "edit.html",
            schedule=defaultdict(
                lambda: "", **{k: v for k, v in dict(schedule).items() if v is not None}
            ),
            type="edit",
            variants=VARIANTS,
            schedules=SCHEDULES,
        )


@app.route("/delete/<id>", methods=["POST"])
def delete(id):
    db = get_db()
    db.cursor().execute("DELETE FROM schedules WHERE id = ?", id)
    db.commit()
    return redirect(url_for("index"))


with app.app_context():
    db = get_db()
    with app.open_resource("schema.sql", mode="r") as f:
        db.cursor().executescript(f.read())
    db.commit()
