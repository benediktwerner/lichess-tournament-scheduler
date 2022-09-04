DROP TABLE badTokens;

CREATE TABLE msgTokens (
    token TEXT NOT NULL,
    team TEXT NOT NULL UNIQUE,
    user TEXT NOT NULL,
    isBad BOOLEAN NOT NULL,
    temporary BOOLEAN NOT NULL
);

CREATE TABLE schedules_new (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    scheduleDay INT NOT NULL,
    scheduleTime INT NOT NULL,
    scheduleStart INT,
    scheduleEnd INT,
    name TEXT NOT NULL,
    team TEXT NOT NULL,
    clock FLOAT NOT NULL,
    increment INT NOT NULL,
    minutes INT NOT NULL,
    variant TEXT NOT NULL,
    rated BOOLEAN NOT NULL,
    position TEXT,
    berserkable BOOLEAN NOT NULL,
    streakable BOOLEAN NOT NULL,
    description TEXT,
    minRating INT,
    maxRating INT,
    minGames INT,
    teamBattleTeams TEXT,
    teamBattleLeaders INT,
    daysInAdvance INT,
    msgMinutesBefore INT,
    msgTemplate TEXT
);

INSERT INTO schedules_new SELECT
    id,
    scheduleDay,
    scheduleTime,
    scheduleStart,
    scheduleEnd,
    name,
    team,
    clock,
    increment,
    minutes,
    variant,
    rated,
    position,
    berserkable,
    streakable,
    description,
    minRating,
    maxRating,
    minGames,
    teamBattleTeams,
    teamBattleLeaders,
    daysInAdvance,
    msgMinutesBefore,
    msgTemplate
 FROM schedules;

DROP TABLE schedules;

ALTER TABLE schedules_new RENAME TO schedules;


CREATE TABLE scheduledMsgs_new (
    arenaId TEXT NOT NULL,
    scheduleId INT NOT NULL,
    team TEXT NOT NULL,
    template TEXT NOT NULL,
    minutesBefore INT NOT NULL,
    sendTime INT NOT NULL
);

INSERT INTO scheduledMsgs_new SELECT
    arenaId,
    scheduleId,
    team,
    template,
    minutesBefore,
    sendTime
 FROM scheduledMsgs;

DROP TABLE scheduledMsgs;

ALTER TABLE scheduledMsgs_new RENAME TO scheduledMsgs;
