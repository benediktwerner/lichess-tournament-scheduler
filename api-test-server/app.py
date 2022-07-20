#!/usr/bin/env python3

from __future__ import annotations

from time import time
from typing import Any

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


@app.route("/api/token/test", methods=["POST"])
def token_test() -> Any:
    token = request.data.decode()
    return jsonify(
        {
            token: {
                "userId": "benwerner",
                "expires": int(time() * 1000) + 60 * 60 * 1000,
                "scopes": "tournament:write,team:write",
            }
        }
    )


@app.route("/api/team/of/<user>")
def teams(user: str) -> Any:
    return jsonify([])


@app.route("/api/team/<team>/arena")
def existing_arenas(team: str) -> Any:
    return ""


@app.route("/api/tournament", methods=["POST"])
def create_arena() -> Any:
    print(request.form)
    return jsonify({"id": "abc"})
