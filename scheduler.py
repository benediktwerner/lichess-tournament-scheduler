from __future__ import annotations

import logging
from datetime import datetime
from threading import Thread
from time import sleep, time
from typing import Any, Dict, List, Optional, Tuple, cast

import api
from db import Db
from model import ScheduleWithId

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SchedulerThread(Thread):
    def __init__(self, api_key: str) -> None:
        super().__init__(daemon=True)
        self.api_key = api_key
        self.arenas_rate_limited_until: Optional[float] = None
        self.msgs_rate_limited_until: Dict[str, float] = {}

    def schedule_next_arenas(self) -> None:
        with Db() as db:
            schedules = db.schedules()

            now = time()
            scheduled = db.get_scheduled()
            to_schedule: List[Tuple[int, ScheduleWithId]] = []
            for s in schedules:
                for nxt in s.next_times():
                    # don't schedule if starting too soon (in <1h)
                    if nxt < now + 60 * 60:
                        continue
                    if (s.id, nxt) in scheduled:
                        continue
                    to_schedule.append((nxt, s))

            # Create soonest tournaments first in case of rate-limiting
            to_schedule.sort(key=lambda x: x[0])

            for nxt, s in to_schedule:
                logger.info(
                    f"Trying to create {s.name} for {s.team} at {nxt} ({datetime.utcfromtimestamp(nxt):%Y-%m-%d %H:%M:%S})"
                )
                if "{nth" in s.name or (s.description and "{nth" in s.description):
                    nth = db.num_created_before(s.id, nxt) + 1
                else:
                    nth = 0
                prev, prev2 = db.previous_two_created(s.id, nxt)
                try:
                    id, name = api.schedule_arena(s, nxt, self.api_key, nth, prev)
                except Exception as e:
                    logger.error(
                        f"Error during tournament creation: {e}", exc_info=True
                    )
                    if hasattr(e, "response"):
                        try:
                            response = cast(Any, e).response
                            logger.error(
                                f"Response: {response.status_code} {response.text}"
                            )
                            if response.status_code == 429:
                                self.arenas_rate_limited_until = now + 60 * 60
                                return
                        except Exception:
                            pass

                    db.insert_created(id, s.id, s.team, nxt, str(e))
                    sleep(10)
                    continue

                db.insert_created(id, s.id, s.team, nxt)
                logger.info(f"Created {name or s.name} as {id}")

                if s.msgMinutesBefore and s.msgMinutesBefore > 0 and s.msgTemplate:
                    db.insert_scheduled_msg(
                        id,
                        s.id,
                        s.team,
                        s.msgTemplate,
                        s.msgMinutesBefore,
                        nxt - s.msgMinutesBefore * 60,
                    )

                sleep(10)
                if prev and s.description and "](next)" in s.description:
                    logger.info(f"Adding link to: {prev}")
                    api.update_link_to_next_arena(
                        prev, prev2, id, s.description, nth - 1, self.api_key
                    )
                    sleep(10)

    def send_scheduled_messages(self) -> None:
        with Db() as db:
            msgs = db.get_and_remove_scheduled_msgs()

        now_timestamp = time()
        now = datetime.utcfromtimestamp(int(now_timestamp))

        for msg in msgs:
            logger.info(
                f"Sending team PM for {msg.arenaId} at {now:%Y-%m-%d %H:%M:%S} (scheduled {datetime.utcfromtimestamp(msg.sendTime):%Y-%m-%d %H:%M:%S})"
            )

            if msg.team in self.msgs_rate_limited_until:
                if self.msgs_rate_limited_until[msg.team] > now_timestamp:
                    logger.warn(f"Skipping team PM due to active rate-limiting")
                    continue
                del self.msgs_rate_limited_until[msg.team]

            with Db() as db:
                token = db.token_for_team(msg.team)

            if not token:
                logger.warn(f"No valid token found")
                continue

            vToken = api.verify_token(token)
            if not vToken or not vToken.is_valid_msg_token_for_team(msg.team):
                logger.warn("Bad token")
                with Db() as db:
                    db.mark_bad_token(msg.team, token)
                continue

            try:
                api.send_team_msg(msg, token)
            except Exception as e:
                logger.error(f"Error during msg sending: {e}", exc_info=True)
                if hasattr(e, "response"):
                    try:
                        response = cast(Any, e).response
                        logger.error(
                            f"Response: {response.status_code} {response.text}"
                        )
                        if response.status_code == 429:
                            self.msgs_rate_limited_until[msg.team] = (
                                now_timestamp + 60 * 60
                            )
                    except Exception:
                        pass

            sleep(5)

    def run(self) -> None:
        while True:
            logger.info("Running scheduling")
            try:
                if (
                    self.arenas_rate_limited_until is None
                    or self.arenas_rate_limited_until < time()
                ):
                    self.schedule_next_arenas()
                self.send_scheduled_messages()
            except Exception as e:
                logger.error(f"Error during scheduling: {e}", exc_info=True)
                if hasattr(e, "response"):
                    try:
                        response = cast(Any, e).response
                        logger.error(
                            f"Response: {response.status_code} {response.text}"
                        )
                        if response.status_code == 429:
                            sleep(60 * 60)
                    except Exception:
                        pass
            sleep(60)
