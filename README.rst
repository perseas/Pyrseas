=======
Pyrseas
=======

.. image:: https://api.travis-ci.org/pyrseas/Pyrseas.png?branch=master
           :target: https://travis-ci.org/pyrseas/Pyrseas

.. image:: https://pypip.in/v/Pyrseas/badge.png
           :target: https://crate.io/packages/Pyrseas/
           :alt: Latest PyPI version

.. image:: https://pypip.in/d/Pyrseas/badge.png
           :target: https://crate.io/packages/Pyrseas/
           :alt: Number of PyPI downloads

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

- PostgreSQL 8.4 or higher

- Python 2.6 or higher

- (planned) Werkzeug

- (planned) Jinja2

License
-------

Pyrseas is free (libre) software and is distributed under the BSD
license.  Please see the LICENSE file for details.
