Known Issues
============

The following summarizes deficiencies in the current release of the
Pyrseas utiltities.  For further details please refer to the
discussions in the pyrseas-general mailing list or the Pyrseas issue
tracker.  Suggestions or patches to deal with these issues are
welcome.

Memory utilization
------------------

The yamltodb utility compares the existing and input metadata by
constructing parallel, in-memory representations of the database
catalogs and the input YAML specification.  If the database has a
large number of objects, e.g., in the thousands of tables, the
utility's memory usage may be noticeable.

Object renaming
---------------

Pyrseas provides support for generating SQL statements to rename
various database objects, e.g., ALTER TABLE t1 RENAME TO t2, using an
'oldname' tag which can be added to objects that support SQL RENAME.
The tag has to be added manually to a YAML specification for yamltodb
to act on it and cannot be kept in the YAML file for subsequent runs.
This is not entirely satisfactory for storing the YAML file in a
version control system.

Multiline Strings
-----------------

The text of function source code, view definitions or object COMMENTs
present a problem when they span multiple lines.  The default YAML
output format is to enclose the entire string in double quotes, to
show newlines that are part of the text as escaped characters (i.e.,
``\n``) and to break the text into lines with a
backslash-newline-indentation-backslash pattern.  For example::

 source: "\n     SELECT inventory_id\n     FROM inventory\n     WHERE film_id =\
   \ $1\n     AND store_id = $2\n     AND inventory_in_stock(inventory_id);\n"

This is not very readable, but it does allow YAML to read it back and
correctly reconstruct the original string.  To improve readability,
Pyrseas 0.7 introduced special processing for these strings.  By using
YAML notation, the same string is represented as follows::

 source: |2

       SELECT inventory_id
       FROM inventory
       WHERE film_id = $1
       AND store_id = $2
       AND NOT inventory_in_stock(inventory_id);

However, due to Python 2.x issues with Unicode, the more readable
format is *only* available if using Python 3.x.

Note also that if your function source code has trailing spaces at the
end of lines, they would normally be represented in the original
default format.  However, in the interest of readability,
:program:`dbtoyaml` will remove the trailing spaces from the text.

Views Dependent on Primary Key
------------------------------

:program:`yamltodb` may fail to recreate a view if it takes advantage
of the Postgres enhancement, introduced in version 9.1, where a
``SELECT`` with ``GROUP BY`` includes columns which are functionally
dependent on the grouped columns and the latter are the primary key of
the table containing the additional columns.  Please refer to the
`GROUP BY dcoumentation
<http://www.postgresql.org/docs/9.1/static/sql-select.html#SQL-GROUPBY>`_
for further details.

A potential workaround, that may be used if such views are not
referenced elsewhere, would be to edit the YAML specification to
remove the views (either all or those affected by this) from a first
pass through :program:`yamltodb`. This should create the tables with
their primary keys and then a second pass will create the views.
