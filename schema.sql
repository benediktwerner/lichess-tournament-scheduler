CREATE TABLE schedules (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    scheduleDay INT NOT NULL, -- 0 every day, 1-7 on that weekday, 1xxx every xxx days, 2xxx every xxx weeks, 3xxx every xxx months
    scheduleTime INT NOT NULL, -- in UTC minutes
    scheduleStart INT, -- unix time in secs when to first schedule this tournament
    scheduleEnd INT, -- unix time in secs when to stop scheduling this tournament
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
    daysInAdvance INT
);

CREATE TABLE createdArenas (
    id TEXT NOT NULL,
    scheduleId INT NOT NULL,
    team TEXT NOT NULL,
    time INT NOT NULL
);

CREATE TABLE logs (
    text TEXT NOT NULL,
    time INT NOT NULL
);
