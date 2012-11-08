CREATE TABLE language (
    language_id INTEGER NOT NULL PRIMARY KEY,
    name VARCHAR(20) NOT NULL,
    last_update TIMESTAMP WITH TIME ZONE NOT NULL
);
ALTER TABLE film ADD COLUMN language_id INTEGER NOT NULL;
ALTER TABLE film ADD FOREIGN KEY (language_id)
    REFERENCES language (language_id);
