CREATE TABLE category (
    category_id SERIAL NOT NULL PRIMARY KEY,
    name VARCHAR(25) NOT NULL,
    last_update TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE TABLE film_category (
    film_id INTEGER NOT NULL REFERENCES film (id),
    category_id INTEGER NOT NULL
        REFERENCES category (category_id),
    last_update TIMESTAMP WITH TIME ZONE NOT NULL,
    PRIMARY KEY (film_id, category_id)
);
