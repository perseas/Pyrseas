yamltodb - YAML to Database
===========================

Name
----

yamltodb -- generate SQL statements to update a PostgreSQL database to
match the schema specified in a YAML file

Synopsys
--------

::

   yamltodb [option...] dbname yamlspec

Description
-----------

:program:`yamltodb` is a utility for generating SQL statements to
update a PostgreSQL database so that it will match the schema
specified in an input `YAML <http://yaml.org>`_ formatted
specification file.

For example, given the input file shown under :doc:`dbtoyaml`,
:program:`yamltodb` outputs the following SQL statements::

 CREATE SCHEMA s1;
 CREATE TABLE t1 (
     c1 integer NOT NULL,
     c2 smallint,
     c3 boolean DEFAULT false,
     c4 text);
 CREATE TABLE s1.t2 (
     c21 integer NOT NULL,
     c22 character varying(16));
 ALTER TABLE s1.t2 ADD CONSTRAINT t2_pkey PRIMARY KEY (c21);
 ALTER TABLE t1 ADD CONSTRAINT t1_pkey PRIMARY KEY (c1);
 ALTER TABLE t1 ADD CONSTRAINT t1_c2_fkey FOREIGN KEY (c2) REFERENCES s1.t2 (c21);

Options
-------

:program:`yamltodb` accepts the following command-line arguments:

dbname

    Specifies the name of the database whose schema is to analyzed.

yamlspec

    Specifies the location of the YAML specification.

-H `host`, --host= `host`

    Specifies the host name of the machine on which the PostgreSQL
    server is running. The default host name is 'localhost'.

-p `port`, --port= `port`

    Specifies the TCP port on which the PostgreSQL server is listening
    for connections. The default port number is 5432.

-U `username`, --user= `username`

    User name to connect as. The default user name is provided by the
    environment variable :envvar:`USER`.

-1, --single-transaction

    Wrap the generated statements in BEGIN/COMMIT. This ensures that
    either all the statements complete successfully, or no changes are
    applied.

Examples
--------

Given a YAML file named `moviesdb.yaml`, to generate SQL statements to
update a database called `mymovies`::

  yamltodb mymovies moviesdb.yaml

To generate the statements as above and immediately update `mymovies`::

  yamltodb mymovies moviesdb.yaml | psql mymovies
