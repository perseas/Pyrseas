CREATE TABLE genre (
    genre_id INTEGER PRIMARY KEY,
    name VARCHAR(25) NOT NULL
);
INSERT INTO genre VALUES
(1, 'Action'),
(2, 'Adventure'),
(3, 'Animation'),
(4, 'Biography'),
(5, 'Comedy'),
(6, 'Crime'),
(7, 'Documentary'),
(8, 'Drama'),
(9, 'Family'),
(10, 'Fantasy'),
(11, 'Film-Noir'),
(12, 'History'),
(13, 'Horror'),
(14, 'Music'),
(15, 'Musical'),
(16, 'Mystery'),
(17, 'Romance'),
(18, 'Sci-Fi'),
(19, 'Sport'),
(20, 'Thriller'),
(21, 'War'),
(22, 'Western');
CREATE TABLE film_genre (
    film_id INTEGER NOT NULL REFERENCES film (id),
    genre_id INTEGER NOT NULL
        REFERENCES genre (genre_id),
    last_update TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (film_id, genre_id)
);
