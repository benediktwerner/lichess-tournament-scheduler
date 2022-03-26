CREATE TABLE schedules_new (
    id INTEGER NOT NULL PRIMARY KEY,
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
    minGames INT
);

INSERT INTO schedules_new SELECT * FROM schedules;

DROP TABLE schedules;

ALTER TABLE schedules_new RENAME TO schedules;
