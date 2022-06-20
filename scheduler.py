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
            to_schedule = []
            for s in schedules:
                for nxt in s.next_times():
                    # don't schedule if starting too soon (in <1h)
                    if nxt < now + 60 * 60:
                        continue
                    if scheduled.is_scheduled(s, nxt):
                        continue
                    to_schedule.append((nxt, s))

            # Create soonest tournaments first in case of rate-limiting
            to_schedule.sort(key=lambda x: x[0])

            for nxt, s in to_schedule:
                db.add_log(f"Trying to create {s.name} for {s.team}")
                id = api.schedule_arena(s, nxt, self.api_key)
                db.insert_created(id, s.id, s.team, nxt)
                db.add_log(f"Created {s.name}")
                sleep(10)

    def run(self) -> None:
        while True:
            with Db() as db:
                db.clean_logs()
                db.add_log("Running scheduling")
            try:
                self.schedule_next_arenas()
            except Exception as e:
                with Db() as db:
                    db.add_log("Error during scheduling")
                self.logger.error(f"Error during tournament creation: {e}")
                if hasattr(e, "response"):
                    try:
                        response = cast(Any, e).response
                        self.logger.error(f"Response: {response.status_code} {response.text}")
                        with Db() as db:
                            db.add_log(f"Response: {response.status_code}")
                    except Exception:
                        pass
            sleep(60 * 60)


class ScheduledCache:
    def __init__(self) -> None:
        self.cache: Dict[str, Set[Arena]] = {}

    def is_scheduled(self, s: Schedule, t: int) -> bool:
        arenas = self.get_arenas(s.team)
        arena = Arena(s.name + " Arena", t)
        team_battle = Arena(s.name + " Team Battle", t)
        return arena in arenas or team_battle in arenas

    def get_arenas(self, team: str) -> Set[Arena]:
        arenas = self.cache.get(team)
        if arenas is None:
            arenas = api.future_team_arenas(team)
            self.cache[team] = arenas
            sleep(10)
        return arenas
