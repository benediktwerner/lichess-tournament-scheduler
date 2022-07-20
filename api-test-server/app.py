#!/usr/bin/env python3

from __future__ import annotations

from time import time

from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)


@app.route("/api/token/test", methods=["POST"])
def token_test() -> str:
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
