CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER NOT NULL PRIMARY KEY,
    scheduleDay INT NOT NULL, -- 0 every day, 1-7 on that weekday
    scheduleTime INT NOT NULL, -- in UTC minutes
    scheduleStart INT, -- unix time in secs when to first schedule this tournament
    scheduleEnd INT, -- unix time in secs when to stop scheduling this tournament
    name TEXT NOT NULL,
    team TEXT NOT NULL,
    clock INT NOT NULL,
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
    minGames INT
);

CREATE TABLE IF NOT EXISTS createdArenas (
    id TEXT NOT NULL,
    team TEXT NOT NULL,
    time INT NOT NULL
);
