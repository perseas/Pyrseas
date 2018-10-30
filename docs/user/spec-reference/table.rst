Table 
===============

https://www.postgresql.org/docs/current/static/sql-createtable.html


description
-----------

columns
--------

type (string)
  The data type of the column. This can include array specifiers. For more information on the data types supported by PostgreSQL, refer to https://www.postgresql.org/docs/current/static/datatype.html
description (string)
  Used to "COMMENT ON COLUMN..." https://www.postgresql.org/docs/current/static/sql-comment.html
privileges (node)
  TODO
  GRANT ... ON ... TO ... https://www.postgresql.org/docs/current/static/sql-grant.html
not_null (boolean)
  whether the column allows NULLs
default (string)
  A default value on INSERT
identity (string)
  Must by either "always" or "by default" and is used "GENERATED { ALWAYS | BY DEFAULT } AS IDENTITY"
collation (string)
  COLLATE ...   
statistics (integer 0 to 10000, or -1)
  See SET STATISTICS in ALTER TABLE https://www.postgresql.org/docs/current/static/sql-altertable.html
inherited (boolean)
  TODO



foreign_keys
------------


primary_key
-----------


check_constraints
-----------------

unique_constraints
------------------



indexes
-------


triggers
--------

owner
-----


privileges
----------


rule
----------

https://www.postgresql.org/docs/current/static/rules.html

Example
---------