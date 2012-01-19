dbenhance - Enhance database
============================

Name
----

dbenhance -- Apply enhancements to a PostgreSQL database

Synopsys
--------

::

   dbenhance [option...] dbname spec

Description
-----------

:program:`dbenhance` is a utility for generating various enhancements,
such as automating denormalizations and standardized audit columns, to
a PostgreSQL database.  The enhancements are specified in a
YAML-formatted ``spec`` file.

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
be enhanced.  Under each table the following values are recognized:

 - audit_trails: This indicates that audit trail columns are to be
   added to the table, e.g., a timestamp column recording when a row
   was last modified.

 - denorm_columns: This lists columns that are to be added to the
   table as a denormalization, for example, a column that exists in
   another table which has a transitive functional dependency on the
   primary key of this table.

 - history_for: This table is to be added to the given schema and will
   hold a history of changes in another table.

:program:`dbenhance` first reads the database catalogs. It also reads
the configuration file ``pyrseas.cfg``, either in the default location
provided with the utility, from the current directory, or from the
location pointed at by the environment variable
PYRSEAS_CONFIG. :program:`dbenhance` then reads the enhancement
specification file and outputs a YAML file, including the existing
catalog information together with the desired enhancements.  The YAML
file is suitable for input to :program:`yamltodb` to generate the SQL
statements to implement the changes.

Options
-------

:program:`dbenhance` accepts the following command-line arguments:

dbname

    Specifies the name of the database whose schema is to enhanced.

spec

    Location of the file with the enhancement specifications.

-\-config `file`

    Use configuration specifications in the given file.

-H `host`, --host= `host`

    Specifies the host name of the machine on which the PostgreSQL
    server is running. The default host name is 'localhost'.

--merge\-config

    Output a merged YAML file, including the database schema, the
    enhancement specification and the configuration information.

--merge\-specs `file`

    Output a merged YAML file including the database schema and the
    enhancement specification to the given `file`.

-n `schema`, --schema= `schema`

    Enhance only a schema matching `schema`. By default, all schemas
    are enhanced.

-o `file`, --output= `file`

    Send output to the specified file. If this is omitted, the
    standard output is used.

-p `port`, --port= `port`

    Specifies the TCP port on which the PostgreSQL server is listening
    for connections. The default port number is 5432.

-t `table`, \--table= `table`

    Enhance only tables matching `table`.

-U `username`, --user= `username`

    User name to connect as. The default user name is provided by the
    environment variable :envvar:`USER`.

-W\, --password

    Force dbenhance to prompt for a password before connecting to a
    database.  If this option is not specified and password
    authentication is required, dbenhance will resort to libpq
    defaults, i.e., `password file
    <http://www.postgresql.org/docs/current/static/libpq-pgpass.html>`_
    or `PGPASSWORD environment variable
    <http://www.postgresql.org/docs/current/static/libpq-envars.html>`_.

Examples
--------

To enhance a database called ``moviesdb`` according to the
specifications in the file ``moviesbl.yaml``::

  dbenhance moviesdb moviesbl.yaml
