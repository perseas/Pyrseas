Known Issues
============

The following summarizes notable deficiencies in the current release
of the Pyrseas utiltities.  For further details please refer to the
discussions in the `Pyrseas issue tracker
<https://github.com/perseas/Pyrseas/issues>`_.  Suggestions or patches
to deal with these issues are welcome.

Coverage of Postgres Objects
----------------------------

An important Pyrseas objective is to support creating, altering or
dropping nearly any Postgres object accessible through SQL, including
adding, modifying or removing any attributes or features of those
objects.  At present, we believe Pyrseas covers roughly over 90% of
the Postgres object/attribute universe.  Please refer to the `Feature
Matrix <https://pyrseas.wordpress.com/feature-matrix/>`_ for details.

This is a continuing effort since Postgres keeps adding new features
in each release, such as the table PARTITIONING syntax in PG 10.  We
have documented current limitations in the issue tracker, see, for
example, issues `135 <https://github.com/perseas/Pyrseas/issues/135>`_
and `178 <https://github.com/perseas/Pyrseas/issues/178>`_. Please
open an issue on the tracker if you find objects or features needing
additional support.

Object Dependencies
-------------------

The first releases of :program:`yamltodb` used a generally fixed
traversal order when generating SQL.  This caused problems with
complex dependencies between objects (e.g., views that depended on
functions that depended on types).  Release 0.8 introduced a
topological sort of objects based on their dependencies.  The
resulting dependency graph is now used to drive SQL generation.  This
should eliminate most object dependency problems seen with the
previous architecture.  However, certain issues still remain.
Specifically, if an object depends on a Postgres internally-defined
object, or on an object defined by a Postgres extension, the Pyrseas
utilities may not behave as expected (see issue `175
<https://github.com/perseas/Pyrseas/issues/175>`_ for additional
discussion).

Object renaming
---------------

Pyrseas provides support for generating SQL statements to rename
various database objects, e.g., ALTER TABLE t1 RENAME TO t2, using an
'oldname' tag which can be added to objects that support SQL RENAME.
The tag has to be added manually to a YAML specification for yamltodb
to act on it and cannot be kept in the YAML file for subsequent runs.
This is not entirely satisfactory for storing the YAML file in a
version control system.

Memory utilization
------------------

The yamltodb utility compares the existing and input metadata by
constructing parallel, in-memory representations of the database
catalogs and the input YAML specification.  If the database has a
large number of objects, e.g., in the thousands of tables, the
utility's memory usage may be noticeable.


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

Index and Partitioning Expressions
----------------------------------

Postgres allows users to create `indexes using expressions
<https://www.postgresql.org/docs/current/static/indexes-expressional.html>`_.
A user can also mix expressions with regular columns.  The Postgres
catalogs store the index information in a bespoke fashion: an array of
column numbers where a zero indicates an expression and a list of
expression trees (an internal format) for the expressions, with
additional arrays for collation information, operator classes and
index options such as ``ASC`` or ``DESC``.  Although the
``pg_get_indexdef`` system catalog function can be used to obtain a
full ``CREATE INDEX`` statement, Pyrseas has chosen to specify each
column or expresssion separately in the YAML definitions.  This has
not been satisfactory in complex cases (see for example issue `170
<https://github.com/perseas/Pyrseas/issues/170>`_) and is an area
requiring further attention.  A similar situation exists for table
partitioning using expresssions.
