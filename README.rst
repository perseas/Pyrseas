=======
Pyrseas
=======

.. image:: https://api.travis-ci.org/perseas/Pyrseas.png?branch=master
           :target: https://travis-ci.org/perseas/Pyrseas

Pyrseas provides utilities to describe a PostgreSQL database schema as
YAML, to verify the schema against the same or a different database
and to generate SQL that will modify the schema to match the YAML
description.

Features
--------

- Outputs a YAML description of a Postgres database's tables
  and other objects (metadata), suitable for storing in a version
  control repository

- Generates SQL statements to modify a database so that it will match
  an input YAML/JSON specification

- Generates an augmented YAML description of a Postgres database
  from its catalogs and an augmentation specification.

Requirements
------------

- PostgreSQL 9.3 or higher

- Python 2.7 or higher

License
-------

Pyrseas is free (libre) software and is distributed under the BSD
license.  Please see the LICENSE file for details.

Documentation
-------------

Please visit `Read the Docs <https://pyrseas.readthedocs.io/en/latest/>`_
for the latest documentation.
