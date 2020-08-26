Pyrseas
=======

Pyrseas provides utilities to describe a PostgreSQL database schema as
YAML, to verify the schema against the same or a different database
and to generate SQL that will modify the schema to match the YAML
description.

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

- `PostgreSQL <https://www.postgresql.org/>`_ 9.4 or higher

- `Python <http://www.python.org/>`_ 2.7, 3.4 or higher

- `Psycopg2 <http://initd.org/psycopg>`_ 2.7 or higher

- `PyYAML <http://pyyaml.org/>`_ 3.13 or higher

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

Currently, the only external APIs are the class
:class:`~pyrseas.database.Database` and the methods
:meth:`~pyrseas.database.Database.to_map` and
:meth:`~pyrseas.database.Database.diff_map` of the latter. Other
classes and methods are documented mainly for developer use.

.. toctree::
   :maxdepth: 2

   dbobject
   database
   schema

Non-schema Objects
~~~~~~~~~~~~~~~~~~
.. toctree::
   :maxdepth: 2

   cast
   eventtrig
   extension
   foreign
   language

Tables and Related Objects
~~~~~~~~~~~~~~~~~~~~~~~~~~
.. toctree::
   :maxdepth: 2

   table
   column
   constraint
   indexes
   rule

Functions, Operators and Triggers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. toctree::
   :maxdepth: 2

   function
   operator
   operfamily
   operclass
   trigger

Types and Other Schema Objects
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
.. toctree::
   :maxdepth: 2

   collation
   conversion
   textsearch
   type

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
