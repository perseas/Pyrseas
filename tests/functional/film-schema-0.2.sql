ALTER TABLE film ADD COLUMN length SMALLINT
    CHECK (length > 0 AND length < 10000);
ALTER TABLE film ADD COLUMN rating CHAR(5);
