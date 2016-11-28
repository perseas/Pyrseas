=======
Pyrseas
=======

.. image:: https://api.travis-ci.org/perseas/Pyrseas.png?branch=master
           :target: https://travis-ci.org/perseas/Pyrseas

Pyrseas provides utilities to compare the schema of a Postgres
database against another, either a previously stored version or from a
different database, and to synchronize the schemas.

Features
--------

- Outputs a YAML description of a PostgreSQL database's tables
  and other objects (metadata), suitable for storing in a version
  control repository

- Generates SQL statements to modify a database so that it will match
  an input YAML/JSON specification

Requirements
------------

- PostgreSQL 9.2 or higher

- Python 2.7 or higher

License
-------

Pyrseas is free (libre) software and is distributed under the BSD
license.  Please see the LICENSE file for details.
