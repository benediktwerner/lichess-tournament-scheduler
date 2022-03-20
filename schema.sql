CREATE TABLE IF NOT EXISTS schedules (
    id INTEGER NOT NULL PRIMARY KEY,
    scheduleDay INT NOT NULL, -- 0 every day, 1-7 on that weekday
    scheduleTime INT NOT NULL, -- in UTC minutes
    name TEXT NOT NULL,
    team TEXT NOT NULL,
    clock INT NOT NULL,
    increment INT NOT NULL,
    minutes INT NOT NULL,
    variant TEXT,
    rated BOOLEAN,
    position TEXT,
    berserkable BOOLEAN,
    streakable BOOLEAN,
    description TEXT,
    minRating INT,
    maxRating INT,
    minGames INT
)
