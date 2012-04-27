dbtoyaml - Database to YAML
===========================

Name
----

dbtoyaml -- extract the schema of a PostgreSQL database in YAML format

Synopsys
--------

::

   dbtoyaml [option...] dbname

Description
-----------

:program:`dbtoyaml` is a utility for extracting the schema of a
PostgreSQL database to a `YAML <http://yaml.org>`_ formatted
specification. Note that `JSON <http://json.org/>`_ is an official
subset of YAML version 1.2, so the :program:`dbtoyaml` output should
also be compatible with JSON tools.

The output format is as follows::

 schema public:
   table t1:
     check_constraints:
       check_expr: (c2 > 123)
       columns:
       - c2
     columns:
     - c1:
         not_null: true
         type: integer
     - c2:
         type: smallint
     - c3:
         default: 'false'
         type: boolean
     - c4:
         type: text
     primary_key:
       t1_pkey:
         access_method: btree
         columns:
         - c1
     foreign_keys:
       t1_c2_fkey:
         columns:
         - c2
         references:
           columns:
           - c21
           schema: s1 
           table: t2
 schema s1:
   table t2:
     columns:
     - c21:
          not_null: true
          type: integer
     - c22:
          type: character varying(16)
     primary_key:
       t2_pkey:
         access_method: btree
         columns:
         - c21

The above should be mostly self-explanatory. The example database has
two tables, named ``t1`` and ``t2``, the first in the ``public``
schema and the second in a schema named ``s1``. The ``columns:``
specifications directly under each table list each column in that
table, in the same order as shown by PostgreSQL. The specifications
``primary_key:``, ``foreign_keys:`` and ``check_constraints:`` define
PRIMARY KEY, FOREIGN KEY and CHECK constraints for a given
table. Additional specifications (not shown) define unique constraints
and indexes.

:program:`dbtoyaml` currently supports extracting information about
nearly all types of PostgreSQL database objects.  See :ref:`api-ref`
for a list of supported objects.

Options
-------

:program:`dbtoyaml` accepts the following command-line arguments (in
addition to the :doc:`cmdargs`):

dbname

    Specifies the name of the database whose schema is to extracted.

-n `schema`, ---schema= `schema`

    Extracts only a schema matching `schema`. By default, all schemas
    are extracted. Multiple schemas can be extracted by using multiple
    ``-n`` switches. Note that normally all objects that belong to the
    schema are extracted as well, unless excluded otherwise.

-N `schema`, ---exclude-schema= `schema`

    Does not extract schema matching `schema`. This can be given more
    than once to exclude several schemas.

-t `table`, ---table= `table`

    Extract only tables matching `table`.  Multiple tables can be
    extracted by using multiple ``-t`` switches.  Note that selecting
    a table may cause other objects, such as an owned sequence, to be
    extracted as well


-T `table`, ---exclude-table= `table`

    Do not extract tables matching `table`.  Multiple tables can be
    excluded by using multiple ``-T`` switches.


Examples
--------

To extract a database called ``moviesdb`` into a file::

  dbtoyaml moviesdb > moviesdb.yaml

To extract only the schema named ``store``::

  dbtoyaml --schema=store moviesdb > moviesdb.yaml

To extract the tables named ``film`` and ``genre``::

  dbtoyaml -t film -t genre moviesdb -o moviesdb.yaml

To extract objects, to standard output, except those in schemas
``product`` and ``store``::

  dbtoyaml -N product -N store moviesdb
