dbtoyaml - Database to YAML
===========================

Name
----

dbtoyaml -- extract the schema of a Postgres database in YAML format

Synopsys
--------

::

   dbtoyaml [option...] dbname

Description
-----------

:program:`dbtoyaml` is a utility for extracting the schema of a
Postgres database to a `YAML <http://yaml.org>`_ formatted
specification.  By default, the specification is output as a single
output stream, which can be redirected or explicitly sent to a file.
As an alternative, the ``--multiple-files`` option allows you to break
down the specification into multiple files, in general, one for each
object (see `Multiple File Output`_).

Note that `JSON <http://json.org/>`_ is an official
subset of YAML version 1.2, so the :program:`dbtoyaml` output should
also be compatible with JSON tools.

A sample of the output format is as follows::

 schema public:
   owner: postgres
   privileges:
   - postgres:
     - all
   - PUBLIC:
     - all
   table t1:
     check_constraints:
       t1_c2_check:
         columns:
         - c2
         expression: (c2 > 123)
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
column in that table, in the same order as shown by Postgres. The
specifications ``primary_key:``, ``foreign_keys:`` and
``check_constraints:`` define PRIMARY KEY, FOREIGN KEY and CHECK
constraints for a given table. Additional specifications (not shown)
define unique constraints and indexes.

User 'bob' has granted all privileges to 'alice' on the ``s1`` schema.
On table ``t2``, he also granted SELECT to PUBLIC; INSERT, UPDATE and
DELETE to 'alice' with GRANT OPTION; and she has in turn granted
INSERT to user 'carol'.

:program:`dbtoyaml` currently supports extracting information about
nearly all types of Postgres database objects.  See :ref:`api-ref`
for a list of supported objects.

The behavior and options of ``dbtoyaml`` are patterned after the
`pg_dump utility
<https://www.postgresql.org/docs/current/static/app-pgdump.html>`_
since it is most analogous to using ``pg_dump --schema-only``.

Multiple File Output
--------------------

.. program:: dbtoyaml

The :option:`--multiple-files` option breaks down the output into
multiple files under a given root directory.  The root is created if
it does not exist.  The root directory name defaults to ``metadata``
in the system configuration file.  The location of the root directory
defaults to the configuration item ``repository.path`` or can be
specified using the `--repository` option (see :doc:`config`
and :doc:`cmdargs` for further details).

The first level contains ``schema.<name>`` subdirectories,
``schema.<name>.yaml`` files and ``<objtype>.<name>.yaml`` files,
where ``<name>`` is the name of the corresponding objects and
``<objtype>`` is the type of top-level (non-schema) object.  Note that
non-schema refers to Postgres extensions, casts, languages or
foreign data wrappers.

The second level, i.e., the ``schema.<name>`` subdirectories contain
``<objtype>.<name>.yaml`` files for each object in the particular
schema (but see below for caveats).

Object Name Conflicts
~~~~~~~~~~~~~~~~~~~~~

The names of Postgres objects can include characters that are not
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
schema object names are truncated to 32 characters.

If two object names, thus transformed, map to the same string, then
the objects' information is written to the same file, e.g.,
``table.my_table.yaml`` in the second example above.  If you prefer to
change the default truncation length, please define the environment
variable ``PYRSEAS_MAX_IDENT_LEN`` to some integer value (up to 63).

Version Control and Dropped Objects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

It is expected that the output of ``dbtoyaml --multiple-files`` will
be placed under version control.  Further invocations should then
update the files in the same directory tree.  However, if an object is
dropped from the database ``dbtoyaml`` would normally only output
files for new or changed objects--and thus keep the dropped object
file under version control.  To deal with dropped objects, ``dbtoyaml
-m`` outputs a special YAML "index" file, named
``database.<dbname>.yaml`` in the root directory.  When ``dbtoyaml
-m`` is run a second time, it looks for this "index" file and if
found, proceeds to delete the previous run's ``.yaml`` files before
outputting new ones.

Options
-------

:program:`dbtoyaml` accepts the following command-line arguments (in
addition to the :doc:`cmdargs`):

dbname

    Specifies the name of the database whose schema is to be extracted.

.. cmdoption:: -m, --multiple-files

    Extracts the schema to a two-level directory tree.  See `Multiple
    File Output`_ above.

.. cmdoption:: -n <schema>
               --schema <schema>

    Extracts only a schema matching `schema`. By default, all schemas
    are extracted. Multiple schemas can be extracted by using multiple
    ``-n`` switches. Note that normally all objects that belong to the
    schema are extracted as well, unless excluded otherwise.

.. cmdoption:: -N <schema>
               --exclude-schema <schema>

    Does not extract schema matching `schema`.  This can be given more
    than once to exclude several schemas.

.. cmdoption:: -O, --no-owner

    Do not output object ownership information.  By default, as seen
    in the sample output above, database objects (schemas, tables,
    etc.) that can be owned by some user, are shown with an "owner:
    *username*" element.  The :option:`-O` switch suppresses all those
    lines.

    NOTE: If you specify `--no-owner`, you will most likely also want
    to specify :option:`--no-privileges`.  If the former is used
    without the latter the resulting YAML output will have privilege
    information without user data, which will cause errors if the YAML
    is then fed to :doc:`yamltodb`.

.. cmdoption:: -t <table>
               --table <table>

    Extract only tables matching `table`.  Multiple tables can be
    extracted by using multiple :option:`-t` switches.  Note that
    selecting a table may cause other objects, such as an owned
    sequence, to be extracted as well

.. cmdoption:: -T <table>
               --exclude-table <table>

    Do not extract tables matching `table`.  Multiple tables can be
    excluded by using multiple :option:`-T` switches.

.. cmdoption:: -x, --no-privileges

    Do not output access privilege information.  By default, as seen
    in the sample output above, if specific GRANTs have been issued on
    various objects (schemas, tables, etc.), the privileges are shown
    under each object.  The :option:`-x` switch suppresses all those
    lines.

    See also the NOTE under :option:`--no-owner`.

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

  dbtoyaml moviesdb -m movies/dbspec
