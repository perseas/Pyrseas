yamltodb - YAML to Database
===========================

Name
----

yamltodb -- generate SQL statements to update a PostgreSQL database to
match the schema specified in a YAML file

Synopsys
--------

::

   yamltodb [option...] dbname [spec]

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

:program:`yamltodb` accepts the following command-line arguments (in
addition to the :doc:`cmdargs`):

**dbname**

    Specifies the name of the database whose schema is to analyzed.

**spec**

    Specifies the location of the YAML specification.  If this is
    omitted or specified as a single or double dash, the specification
    is read from the program's standard input.

-n **schema**, ``--schema=`` **schema**

    Compare only a schema matching **schema**.  By default, all schemas
    are compared.  Multiple schemas can be compared by using multiple
    ``-n`` switches.

-1\, ``--single-transaction``

    Wrap the generated statements in BEGIN/COMMIT. This ensures that
    either all the statements complete successfully, or no changes are
    applied.

-u\, ``--update``

    Execute the generated statements against the database mentioned in
    **dbname**.  This implies the ``--single-transaction`` option.

Examples
--------

Given a YAML file named ``moviesdb.yaml``, to generate SQL statements
to update a database called `mymovies`::

  yamltodb mymovies moviesdb.yaml

To generate the statements as above and immediately update `mymovies`::

  yamltodb mymovies moviesdb.yaml | psql mymovies

or::

  yamltodb --update mymovies moviesdb.yaml

To generate the statements directly from the ouput of
:program:`dbtoyaml` (against a different database), with statements
enclosed in a single transaction, and save the statements in a file
named ``mymovies.sql``::

  dbtoyaml devmovies | yamltodb -1 mymovies -o mymovies.sql
