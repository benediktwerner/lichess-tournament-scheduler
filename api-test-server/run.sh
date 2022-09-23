#!/bin/sh

source ../venv/bin/activate
FLASK_ENV=development flask run --no-reload --port 3333
