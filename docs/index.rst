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

- `PostgreSQL <https://www.postgresql.org/>`_ 9.3 or higher

- `Python <http://www.python.org/>`_ 2.7 or higher

Installation
------------

For the latest release, use::

 pip install Pyrseas


Contents
--------

.. toctree::
   :maxdepth: 2

   overview
   user/index
.. toctree::
   :maxdepth: 1

   devel/index



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
