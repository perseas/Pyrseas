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

Delimited identifiers
---------------------

PostgreSQL supports SQL delimited identifiers, i.e., object
identifiers that include special characters (e.g., spaces, minus
signs) or that are SQL reserved words.  Pyrseas currently supports the
first type of delimited identifiers, but not the use of reserved
words, such as the tables named "order" or columns named "limit."
Some work is in progress to address this issue.
