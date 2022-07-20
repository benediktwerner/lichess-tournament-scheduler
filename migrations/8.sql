DROP TABLE logs;

ALTER TABLE schedules
  ADD msgMinutesBefore INT;

ALTER TABLE schedules
  ADD msgTemplate TEXT;

ALTER TABLE schedules
  ADD msgToken TEXT;

CREATE TABLE scheduledMsgs (
    arenaId TEXT NOT NULL,
    scheduleId INT NOT NULL,
    team TEXT NOT NULL,
    template TEXT NOT NULL,
    token TEXT NOT NULL,
    minutesBefore INT NOT NULL,
    sendTime INT NOT NULL
);

CREATE TABLE badTokens (
    token TEXT NOT NULL,
    team TEXT NOT NULL
);
