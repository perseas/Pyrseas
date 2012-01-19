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

 schema public:
   table t1:
     audit_trails: default
   table t3:
     audit_trails: last_modified_only
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

 - audit_trails: This indicates that audit trail columns are to be
   added to the table, e.g., a timestamp column recording when a row
   was last modified.

 - denorm_columns: This lists columns that are to be added to the
   table as a denormalization, for example, a column that exists in
   another table which has a transitive functional dependency on the
   primary key of this table.

 - history_for: This table is to be added to the given schema and will
   hold a history of changes in another table.

:program:`dbextend` first reads the database catalogs.  It also reads
a configuration, either internal or external, from a file in the
current directory, or from the location pointed at by the environment
variable PYRSEAS_CONFIG. :program:`dbextend` then reads the extension
specification file and outputs a YAML file, including the existing
catalog information together with the desired enhancements.  The YAML
file is suitable for input to :program:`yamltodb` to generate the SQL
statements to implement the changes.

Options
-------

:program:`dbextend` accepts the following command-line arguments:

dbname

    Specifies the name of the database whose schema is to augmented.

spec

    Location of the file with the extension specifications.

-\-config `file`

    Use configuration specifications in the given file.

-H `host`, --host= `host`

    Specifies the host name of the machine on which the PostgreSQL
    server is running. The default host name is 'localhost'.

--merge\-config

    Output a merged YAML file, including the database schema, the
    extension specification and the configuration information.

--merge\-specs `file`

    Output a merged YAML file including the database schema and the
    extension specification to the given `file`.

-n `schema`, --schema= `schema`

    Extend only a schema matching `schema`. By default, all schemas
    are affected.  Multiple schemas can be augmented by using multiple
    ``-n` switches.

-o `file`, --output= `file`

    Send output to the specified file. If this is omitted, the
    standard output is used.

-p `port`, --port= `port`

    Specifies the TCP port on which the PostgreSQL server is listening
    for connections. The default port number is 5432.

-t `table`, \--table= `table`

    Extend only tables matching `table`.

-U `username`, --user= `username`

    User name to connect as. The default user name is provided by the
    environment variable :envvar:`USER`.

-W\, --password

    Force dbextend to prompt for a password before connecting to a
    database.  If this option is not specified and password
    authentication is required, dbextend will resort to libpq
    defaults, i.e., `password file
    <http://www.postgresql.org/docs/current/static/libpq-pgpass.html>`_
    or `PGPASSWORD environment variable
    <http://www.postgresql.org/docs/current/static/libpq-envars.html>`_.

Examples
--------

To extend a database called ``moviesdb`` according to the
specifications in the file ``moviesbl.yaml``::

  dbextend moviesdb moviesbl.yaml
