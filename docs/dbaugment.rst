dbaugment - Augment a database
==============================

Name
----

dbaugment -- Augment a PostgreSQL database in predefined ways

Synopsys
--------

::

   dbaugment [option...] dbname [spec]

Description
-----------

:program:`dbaugment` is a utility for augmenting a PostgreSQL database
with various standard attributes and procedures, such as automatically
maintained audit columns.  The augmentations are defined in a
YAML-formatted ``spec`` file.

The specification file format is as follows::

 augmenter:
   columns:
     modified_date:
       not_null: true
       type: date
 schema public:
   table t1:
     audit_columns: default
   table t3:
     audit_columns: modified_only

The specification file lists each schema, and within it, each table to
be augmented.  Under each table the following values are recognized:

 - audit_columns: This indicates that audit trail columns are to be
   added to the table, e.g., a timestamp column recording when a row
   was last modified.

The first section of the specification file, under the ``augmenter``
header, lists configuration information. This is in addition to the
built-in configuration objects (see :ref:`predef-aug`).

:program:`dbaugment` first reads the database catalogs.  It also
initializes itself from predefined configuration information.
:program:`dbaugment` then reads the specification file, which may
include additional configuration objects, and outputs a YAML file,
including the existing catalog information together with the desired
enhancements.  The YAML file is suitable for input to
:program:`yamltodb` to generate the SQL statements to implement the
changes.

Options
-------

:program:`dbaugment` accepts the following command-line arguments (in
addition to the :doc:`cmdargs`):

**dbname**

    Specifies the name of the database whose schema is to augmented.

**spec**

    Location of the file with the augmenter specifications.  If this
    is omitted, the specification is read from the program's standard
    input.

.. program:: dbaugment

.. cmdoption:: --merge-config

    Output a merged YAML file, including the database schema, the
    augmenter specification and the configuration information.

.. cmdoption:: --merge-specs <file>

    Output a merged YAML file including the database schema and the
    augmenter specification to the given `file`.

Examples
--------

To augment a database called ``moviesdb`` according to the
specifications in the file ``moviesbl.yaml``::

  dbaugment moviesdb moviesbl.yaml

See Also
--------

  :ref:`predef-aug`
