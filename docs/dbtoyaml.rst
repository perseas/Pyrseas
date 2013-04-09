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
specification.  By default, the specification is output as a single
output stream, which can be redirected or explicitly sent to a file.
As an alternative, the ``--directory`` option allows you to break down
the specification into multiple files, one for each object (see
`Directory Tree Output`_).

Note that `JSON <http://json.org/>`_ is an official
subset of YAML version 1.2, so the :program:`dbtoyaml` output should
also be compatible with JSON tools.

The output format is as follows::

 schema public:
   owner: postgres
   privileges:
   - postgres:
     - all
   - PUBLIC:
     - all
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
     foreign_keys:
       t1_c2_fkey:
         columns:
         - c2
         references:
           columns:
           - c21
           schema: s1 
           table: t2
     owner: alice
     primary_key:
       t1_pkey:
         columns:
         - c1
 schema s1:
   owner: bob
   privileges:
   - bob:
     - all
   - alice:
     - all
   table t2:
     columns:
     - c21:
          not_null: true
          type: integer
     - c22:
          type: character varying(16)
     owner: bob
     primary_key:
       t2_pkey:
         columns:
         - c21
     privileges:
     - bob:
       - all
     - PUBLIC:
       - select
     - alice:
       - insert:
           grantable: true
       - delete:
           grantable: true
       - update:
           grantable: true
     - carol:
         grantor: alice
         privs:
         - insert


The above should be mostly self-explanatory. The example database has
two tables, named ``t1`` and ``t2``, the first --owned by user
'alice'-- in the ``public`` schema and the second --owned by user
'bob'-- in a schema named ``s1`` (also owned by 'bob').
The ``columns:`` specifications directly under each table list each
column in that table, in the same order as shown by PostgreSQL. The
specifications ``primary_key:``, ``foreign_keys:`` and
``check_constraints:`` define PRIMARY KEY, FOREIGN KEY and CHECK
constraints for a given table. Additional specifications (not shown)
define unique constraints and indexes.

User 'bob' has granted all privileges to 'alice' on the ``s1`` schema.
On table ``t2``, he also granted SELECT to PUBLIC; INSERT, UPDATE and
DELETE to 'alice' with GRANT OPTION; and she has in turn granted
INSERT to user 'carol'.

:program:`dbtoyaml` currently supports extracting information about
nearly all types of PostgreSQL database objects.  See :ref:`api-ref`
for a list of supported objects.

Directory Tree Output
---------------------

The ``--directory`` option (see below) breaks down the output into
multiple files under a given root directory.  The root is created if
it does not exist.

The first level contains ``schema.<name>`` subdirectories,
``schema.<name>.yaml`` files and ``<objtype>.<name>.yaml`` files,
where ``<name>`` is the name of the corresponding objects and
``<objtype>`` is the type of top-level (non-schema) object.  Note that
non-schema refers to PostgreSQL extensions, casts, languages or
foreign data wrappers.

The second level, i.e., the ``schema.<name>`` subdirectories contain
``<objtype>.<name>.yaml`` files for each object in the particular
schema (but see below for caveats).

Object Name Conflicts
~~~~~~~~~~~~~~~~~~~~~

The names of PostgreSQL objects can include characters that are not
allowed in filesystem object names.  The most common example is the
division operator ('/'), but even table names can include
non-alphanumeric characters, if the identifiers are quoted.

In addition, one can define two or more objects with the same base
name, e.g., function ``foo(integer)`` and function ``foo(text)``, or a
table named ``"My Table"`` and another named ``"my table"`` or
``"MY TABLE"``. On certain operating systems, i.e., Windows, it is not
possible to create two files in the same directory that differ only in
the case of their characters.

In order to deal with the aforementioned issues, ``dbtoyaml`` places
certain objects in common files and transforms object identifiers so
that they are suitable for use in files and directories.  For example,
the information for all user-defined casts are written to the file
``cast.yaml`` in the root directory.  Functions with the same name but
different arguments are written to a single file, e.g.,
``function.foo.yaml`` in the first example above.  Identifiers are
also converted to all lowercase, non-alphanumeric characters
(excluding underscore) are converted to underscores and, by default,
object names are truncated to 16 characters.

If two object names, thus transformed, map to the same string, then
the objects' information is written to the same file, e.g.,
``table.my_table.yaml`` in the second example above.  If you prefer to
change the default truncation length, please define the environment
variable ``PYRSEAS_MAX_IDENT_LEN`` to some integer value (up to 63).

Version Control and Dropped Objects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is expected that the output of ``dbtoyaml --directory`` will be
placed under version control.  Further invocations should then update
the files in the same directory tree.  However, if an object is
dropped from the database ``dbtoyaml`` would normally only output
files for new or changed objects--and thus keep the dropped object
file under version control.  To deal with dropped objects, ``dbtoyaml
-d`` outputs a special YAML "index" file, named
``database.<dbname>.yaml`` in the root directory.  When ``dbtoyaml
-d`` is run a second time, it looks for this "index" file and if
found, proceeds to delete the previous run's ``.yaml`` files before
outputting new ones.

Options
-------

:program:`dbtoyaml` accepts the following command-line arguments (in
addition to the :doc:`cmdargs`):

dbname

    Specifies the name of the database whose schema is to extracted.

-d **directory**, ``--directory`` **directory**

    Extracts the schema to a two-level directory tree where
    **directory** is the root of the tree.  See `Directory Tree
    Output`_ above.

-n `schema`, ---schema= `schema`

    Extracts only a schema matching `schema`. By default, all schemas
    are extracted. Multiple schemas can be extracted by using multiple
    ``-n`` switches. Note that normally all objects that belong to the
    schema are extracted as well, unless excluded otherwise.

-N `schema`, ---exclude-schema= `schema`

    Does not extract schema matching `schema`. This can be given more
    than once to exclude several schemas.

-O, ---no-owner

    Do not output object ownership information.  By default, as seen
    in the sample output above, database objects (schemas, tables,
    etc.) that can be owned by some user, are shown with an "owner:
    *username*" element.  The ``-O`` switch suppresses all those
    lines.

-t `table`, ---table= `table`

    Extract only tables matching `table`.  Multiple tables can be
    extracted by using multiple ``-t`` switches.  Note that selecting
    a table may cause other objects, such as an owned sequence, to be
    extracted as well

-T `table`, ---exclude-table= `table`

    Do not extract tables matching `table`.  Multiple tables can be
    excluded by using multiple ``-T`` switches.

-x, ---no-privileges

    Do not output access privilege information.  By default, as seen
    in the sample output above, if specific GRANTs have been issued on
    various objects (schemas, tables, etc.), the privileges are shown
    under each object.  The ``-x`` switch suppresses all those lines.

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

To extract objects to a directory under version control::

  dbtoyaml moviesdb -d movies/dbspec
