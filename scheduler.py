from __future__ import annotations

from threading import Thread
from time import sleep, time
from typing import Dict, Set

from flask import current_app

import api
from api import Arena
from db import Db, Schedule


class SchedulerThread(Thread):
    def __init__(self, api_key: str) -> None:
        super().__init__(daemon=True)
        self.api_key = api_key

    def schedule_next_arenas(self) -> None:
        with Db() as db:
            schedules = db.schedules()

        now = time()
        scheduled = ScheduledCache()
        for s in schedules:
            nxt = s.next_time()
            if nxt is None or nxt < now - 60 * 60 or now + 24 * 60 * 60 < now:
                continue
            if scheduled.is_scheduled(s, nxt):
                continue
            api.schedule_arena(s, nxt, self.api_key)
            sleep(10)

    def run(self) -> None:
        while True:
            try:
                self.schedule_next_arenas()
            except Exception as e:
                current_app.logger.error(f"Error during tournament creation: {e}")
            sleep(60 * 60)


class ScheduledCache:
    def __init__(self) -> None:
        self.cache: Dict[str, Set[Arena]] = {}

    def is_scheduled(self, s: Schedule, t: int) -> bool:
        return Arena(s.name, t) in self.get_arenas(s.team)

    def get_arenas(self, team: str) -> Set[Arena]:
        arenas = self.cache.get(team)
        if arenas is None:
            sleep(10)
            arenas = api.future_team_arenas(team)
            self.cache[team] = arenas
        return arenas
