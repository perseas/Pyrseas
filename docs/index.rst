Pyrseas
=======

Pyrseas provides utilities to compare the schema of a Postgres
database against another, either a previously stored version or from a
different database, and to synchronize the schemas.

Features
--------

- Outputs a YAML/JSON description of a PostgreSQL database's tables
  and other objects (metadata), suitable for storing in a version
  control repository

- Generates SQL statements to modify a database so that it willl match
  an input YAML/JSON specification

- Generates an augmented YAML description of a PostgreSQL database
  from its catalogs and an augmentation specification.

Requirements
------------

- `PostgreSQL <http://www.postgresql.org/>`_ 9.2 or higher

- `Python <http://www.python.org/>`_ 2.7 or higher

Contents
--------

.. toctree::
   :maxdepth: 2

   overview
   install
   config
   configitems
   devel
   testing
   issues
   predefaug
.. toctree::
   :maxdepth: 1

   dbaugment
   dbtoyaml
   yamltodb
   cmdargs

.. _api-ref:

API Reference
-------------

Currently, the only external APIs are the classes
:class:`~pyrseas.lib.dbconn.DbConnection` and
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
   collation
   conversion
   eventtrig
   extension
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
   foreign


Augmenter API Reference
-----------------------

.. toctree::
   :maxdepth: 2

   augmentdb
   cfgobjects
   augobjects


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
