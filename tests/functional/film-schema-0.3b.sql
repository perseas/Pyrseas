CREATE TABLE genre (
    genre_id INTEGER PRIMARY KEY,
    name VARCHAR(25) NOT NULL
);
CREATE TABLE film_genre (
    film_id INTEGER NOT NULL REFERENCES film (id),
    genre_id INTEGER NOT NULL
        REFERENCES genre (genre_id),
    last_update TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (film_id, genre_id)
);
