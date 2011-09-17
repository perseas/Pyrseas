Pyrseas
=======

Pyrseas provides a framework and utilities to upgrade and maintain a
relational database.  Its purpose is to enhance and follow through on
the concepts of the `Andromeda Project
<http://www.andromeda-project.org/>`_. The name comes from `Python
<http://www.python.org/>`_, the programming language, and `Perseas
<http://en.wikipedia.org/wiki/Perseus>`_ [#]_, the Greek mythological hero
who rescued Andromeda from a sea monster [#]_.

Pyrseas currently includes the dbtoyaml utility to create a `YAML
<http://yaml.org/>`_ description of a PostgreSQL database's tables,
and the yamltodb utility to generate SQL statements to modify a
database to match an input YAML specification.


Contents:

.. toctree::
   :maxdepth: 2

   overview
   install
   testing
.. toctree::
   :maxdepth: 1

   dbtoyaml
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


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. rubric:: Footnotes

.. [#] The common English name for Perseas is Perseus and the Ancient
   Greek name is Perseos. However, in modern Greek Περσέας_ is the
   more common spelling for the mythical hero. The project would be
   Πυρσέας or ΠΥΡΣΕΑΣ in Greek.

.. _Περσέας: http://en.wiktionary.org/wiki/%CE%A0%CE%B5%CF%81%CF%83%CE%AD%CE%B1%CF%82

.. [#] He is better known for having killed Medusa.

