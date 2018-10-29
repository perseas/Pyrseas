Getting Started
===============


Requirements
------------

Install Postgres
~~~~~~~~~~~~~~~~

Pyrseas provides tools for `Postgres <https://www.postgresql.org>`_,
so you need **Postgres** to start with.  Pyrseas has been
tested with PG 9.3, 9.4, 9.5, 9.6 and 10, and we'll certainly keep up
with future releases.  Please refer to the `Postgres download page
<https://www.postgresql.org/download>`_ to find a distribution for the
various Linux, Unix and Windows platforms supported.

Install Python
~~~~~~~~~~~~~~

You will also need **Python**.  Pyrseas was originally developed using
Python 2 and been tested with `Python <http://www.python.org>`_ 2.7,
but may also work under 2.6.  It has been ported to Python 3 and
tested against versions from 3.2 through 3.6.  Python 3 is the
preferred usage and development environment.  On Linux or \*BSD,
Python may already be part of your distribution or may be available as
a package.  For Windows and Mac OS please refer to the `Python
download page <http://www.python.org/downloads/>`_ for installers and
instructions.


Install Pyrseas
---------------

For the latest release, use::

 pip install Pyrseas

Verify Pyrseas is installed
---------------------------

run::

 yamltodb --version

It should print the version you have installed, for example::

 $ yamltodb --version
 yamltodb 0.8.0

Create an empty Postgres database
---------------------------------

In Postgres, run::

 CREATE DATABASE pyrseas_sample

Create a yaml spec
------------------

Create a text file called pyrseas-sample.yaml::

 schema public:
   owner: postgres
   privileges:
     - posgres:
       - all
   table pyrseas:
     columns:
      - pyrseas_id:        {not_null: true, type: bigint}
     primary_key:
       pk_pyrseas:           { columns: [ pyrseas_id ] }

 extension plpgsql:
   description: PL/pgSQL procedural language
   owner: postgres
   schema: pg_catalog
   version: '1.0'


Run yamltodb
------------

Run the following command to deploy the schema::

 yamltodb -U postgres -W -u pyrseas_sample pyrseas-sample.yaml

The output should look like::

 $ yamltodb -U postgres -W -u pyrseas_sample pyrseas-sample.yaml
 Password:
 BEGIN;
 COMMENT ON SCHEMA public IS NULL;
 
 CREATE TABLE pyrseas (
     pyrseas_id bigint NOT NULL);
 
 ALTER TABLE pyrseas ADD CONSTRAINT pk_pyrseas PRIMARY KEY (pyrseas_id);
 
 COMMIT;
 Changes applied

Congratulations
---------------

You've deployed your first database via Pyrseas.
	