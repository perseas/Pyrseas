=======
Pyrseas
=======

.. image:: https://api.travis-ci.org/perseas/Pyrseas.png?branch=master
           :target: https://travis-ci.org/perseas/Pyrseas

Pyrseas provides a framework and utilities to upgrade and maintain a
PostgreSQL database.

Features
--------

- Outputs a YAML description of a PostgreSQL database's tables
  and other objects (metadata), suitable for storing in a version
  control repository

- Generates SQL statements to modify a database so that it will match
  an input YAML/JSON specification

- (planned) Generates a flexible web application to update PostgreSQL
  tables

Requirements
------------

- PostgreSQL 9.0 or higher

- Python 2.6 or higher

- (planned) Werkzeug

- (planned) Jinja2

License
-------

Pyrseas is free (libre) software and is distributed under the BSD
license.  Please see the LICENSE file for details.
