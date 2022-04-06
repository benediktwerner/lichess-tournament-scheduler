from __future__ import annotations

from logging import Logger
from threading import Thread
from time import sleep, time
from typing import Any, Dict, Set, cast

import api
from api import Arena
from db import Db, Schedule


class SchedulerThread(Thread):
    def __init__(self, api_key: str, logger: Logger) -> None:
        super().__init__(daemon=True)
        self.api_key = api_key
        self.logger = logger

    def schedule_next_arenas(self) -> None:
        with Db() as db:
            db.delete_past_created()
            schedules = db.schedules()

            now = time()
            scheduled = ScheduledCache()
            for s in schedules:
                nxt = s.next_time()
                # don't schedule if starting too soon (in <1h)
                # or in more than 24h
                if nxt is None or nxt < now + 60 * 60 or now + 24 * 60 * 60 < nxt:
                    continue
                if scheduled.is_scheduled(s, nxt):
                    continue
                id = api.schedule_arena(s, nxt, self.api_key)
                db.insert_created(id, s.team, nxt)
                sleep(10)

    def run(self) -> None:
        while True:
            try:
                self.schedule_next_arenas()
            except Exception as e:
                self.logger.error(f"Error during tournament creation: {e}")
                if hasattr(e, "response"):
                    try:
                        self.logger.error(f"Response: {cast(Any, e).response.text}")
                    except Exception:
                        pass
            sleep(60 * 60)


class ScheduledCache:
    def __init__(self) -> None:
        self.cache: Dict[str, Set[Arena]] = {}

    def is_scheduled(self, s: Schedule, t: int) -> bool:
        return Arena(s.name + " Arena", t) in self.get_arenas(s.team)

    def get_arenas(self, team: str) -> Set[Arena]:
        arenas = self.cache.get(team)
        if arenas is None:
            arenas = api.future_team_arenas(team)
            self.cache[team] = arenas
            sleep(10)
        return arenas
