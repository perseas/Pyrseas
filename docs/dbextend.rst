dbextend - Extend a database
============================

Name
----

dbextend -- Augment a PostgreSQL database with standard extensions

Synopsys
--------

::

   dbextend [option...] dbname spec

Description
-----------

:program:`dbextend` is a utility for augmenting a PostgreSQL database
with various standard extensions, such as controlled denormalizations
and automatically maintained audit columns.  The extensions are
specified in a YAML-formatted ``spec`` file.

The specification file format is as follows::

 extender:
   columns:
     modified_date:
       not_null: true
       type: date
 schema public:
   table t1:
     audit_columns: default
   table t3:
     audit_columns: last_modified_only
   table t4:
     denorm_columns:
     - c45:
       depends_on:
         schema: public
         table: t3
         column: c32
 schema s1:
   table t2:
     history_for:
       schema: public
       table: t1
     exclude_columns:
     - c15

The specification file lists each schema, and within it, each table to
be augmented.  Under each table the following values are recognized:

 - audit_columns: This indicates that audit trail columns are to be
   added to the table, e.g., a timestamp column recording when a row
   was last modified.

 - denorm_columns: This lists columns that are to be added to the
   table as a denormalization, for example, a column that exists in
   another table which has a transitive functional dependency on the
   primary key of this table.

 - history_for: This table is to be added to the given schema and will
   hold a history of changes in another table.

The first section of the specification file, under the ``extender``
header, lists configuration information. This is in addition to the
built-in configuration objects (see :ref:`predef-ext`).

:program:`dbextend` first reads the database catalogs.  It also
initializes itself from pre-defined configuration information.
:program:`dbextend` then reads the extension specification file, which
may include additional configuration objects, and outputs a YAML file,
including the existing catalog information together with the desired
enhancements.  The YAML file is suitable for input to
:program:`yamltodb` to generate the SQL statements to implement the
changes.

Options
-------

:program:`dbextend` accepts the following command-line arguments (in
addition to the :doc:`cmdargs`):

dbname

    Specifies the name of the database whose schema is to augmented.

spec

    Location of the file with the extension specifications.

---merge-config

    Output a merged YAML file, including the database schema, the
    extension specification and the configuration information.

---merge-specs `file`

    Output a merged YAML file including the database schema and the
    extension specification to the given `file`.

Examples
--------

To extend a database called ``moviesdb`` according to the
specifications in the file ``moviesbl.yaml``::

  dbextend moviesdb moviesbl.yaml

See Also
--------

  :ref:`predef-ext`
