from __future__ import annotations

import logging
from threading import Thread
from time import sleep, time
from typing import Any, Dict, List, Set, Tuple, cast
from datetime import datetime

import api
from api import Arena
from db import Db
from model import Schedule, ScheduleWithId


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SchedulerThread(Thread):
    def __init__(self, api_key: str) -> None:
        super().__init__(daemon=True)
        self.api_key = api_key

    def schedule_next_arenas(self) -> None:
        with Db() as db:
            schedules = db.schedules()

            now = time()
            scheduled = ScheduledCache()
            to_schedule: List[Tuple[int, ScheduleWithId]] = []
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
                logger.info(
                    f"Trying to create {s.name} for {s.team} at {nxt} ({datetime.utcfromtimestamp(nxt):%Y-%m-%d %H:%M:%S})"
                )
                prev = db.previous_created(s.id, nxt)
                id = api.schedule_arena(s, nxt, self.api_key, prev)
                db.insert_created(id, s.id, s.team, nxt)
                logger.info(f"Created {s.name} as {id}")

                if (
                    s.msgMinutesBefore
                    and s.msgMinutesBefore > 0
                    and s.msgTemplate
                    and s.msgToken
                ):
                    db.insert_scheduled_msg(
                        id,
                        s.id,
                        s.team,
                        s.msgTemplate,
                        s.msgToken,
                        s.msgMinutesBefore,
                        nxt - s.msgMinutesBefore * 60,
                    )

                sleep(10)
                if prev and s.description and "](next)" in s.description:
                    logger.info(f"Adding link to: {prev}")
                    api.update_link_to_next_arena(prev, id, self.api_key)
                    sleep(10)

    def send_scheduled_messages(self) -> None:
        with Db() as db:
            msgs = db.get_and_remove_scheduled_msgs()
            bad_tokens = db.bad_tokens()

        good_tokens = set()

        for msg in msgs:
            logger.info(f"Sending team PM for {msg.arenaId}")

            if (msg.token, msg.team) in bad_tokens:
                logger.warn("Known bad token")
                continue

            if (msg.token, msg.team) not in good_tokens:
                token = api.verify_token(msg.token)
                if token.expired or not token.allows_teams:
                    bad_tokens.add((msg.token, msg.team))
                    logger.warn(f"Bad token")
                    with Db() as db:
                        db.insert_bad_token(msg.token, msg.team)
                    continue
                else:
                    good_tokens.add((msg.token, msg.team))

            api.send_team_msg(msg)
            sleep(5)

    def run(self) -> None:
        while True:
            logger.info("Running scheduling")
            try:
                self.schedule_next_arenas()
                self.send_scheduled_messages()
            except Exception as e:
                logger.error(f"Error during scheduling: {e}")
                if hasattr(e, "response"):
                    try:
                        response = cast(Any, e).response
                        logger.error(
                            f"Response: {response.status_code} {response.text}"
                        )
                    except Exception:
                        pass
            sleep(5 * 60)


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
