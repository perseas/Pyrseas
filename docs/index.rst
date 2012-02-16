Pyrseas
=======

Pyrseas provides a framework and utilities to upgrade and maintain a
PostgreSQL database.

Features
--------

- Outputs a YAML/JSON description of a PostgreSQL database's tables
  and other objects (metadata), suitable for storing in a version
  control repository

- Generates SQL statements to modify a database so that it willl match
  an input YAML/JSON specification

- Generates an extended YAML/JSON description of a PostgreSQL database
  from its catalogs and from an extension specification.

- (planned) Generates a flexible web application to update PostgreSQL
  tables

Requirements
------------

- `PostgreSQL <http://www.postgresql.org/>`_ 8.4 or higher

- `Python <http://www.python.org/>`_ 2.6 or higher

- (planned) Werkzeug

- (planned) Jinja2

Contents
--------

.. toctree::
   :maxdepth: 2

   overview
   install
   testing
   issues
.. toctree::
   :maxdepth: 1

   dbtoyaml
   dbextend
   predefext
   yamltodb

API Reference
-------------

Currently, the only external APIs are the classes
:class:`~pyrseas.dbconn.DbConnection` and
:class:`~pyrseas.database.Database` and the methods
:meth:`~pyrseas.database.Database.to_map` and
:meth:`~pyrseas.database.Database.diff_map` of the latter. Other
classes and methods are documented mainly for developer use.

.. toctree::
   :maxdepth: 2

   dbobject
   dbconn
   database
   cast
   language
   schema
   conversion
   function
   operator
   operfamily
   operclass
   type
   table
   column
   constraint
   indexes
   rule
   trigger
   textsearch

Extender API Reference
----------------------

.. toctree::
   :maxdepth: 2

   extenddb
   cfgobjects
   extobjects


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
