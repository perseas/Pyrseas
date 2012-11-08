CREATE TABLE film (
    id INTEGER NOT NULL PRIMARY KEY,
    title VARCHAR(32) NOT NULL,
    release_year INTEGER NOT NULL CHECK (release_year >= 1888)
);
