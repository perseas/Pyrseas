.. -*- coding: utf-8 -*-

Overview
========

Main Tools
----------

Pyrseas provides utilities to maintain a `PostgreSQL
<https://www.postgresql.org/>`_ database schema by incrementally 
upgrading the schema.

:program:`dbtoyaml` is used to export the database structure (tables, functions, etc) to a yaml file.*

:program:`yamltodb` is used to incrementally upgrade the target database using 
the desired schema in the yaml file.

See :doc:`user/gettingstarted` for a concrete example of how this might work.

\* Multiple yaml files is also supported, see `--multiple-files` in :doc:`user/command-line/dbtoyaml`

Additional Tools
-------------------

:doc:`user/advanced/dbaugment` is used to add the same column/trigger/etc to every table.

:doc:`user/advanced/datacopy` is used to populate tables with static data rows.

:doc:`user/advanced/preactions` is a folder of SQL files for complex migration
scenarios.



Naming
------

The project name comes from `Python <https://www.python.org/>`_, the
programming language, and `Perseas
<https://en.wikipedia.org/wiki/Perseus>`_ [#]_, the Greek mythological
hero who rescued Andromeda from a sea monster [#]_.  It is hoped that
Pyrseas will rescue the Andromeda project <grin>.  You can pronounce
Pyrseas like the hero.


.. rubric:: Footnotes

.. [#] The common English name for Perseas is Perseus and the Ancient
   Greek name is Perseos. However, in modern Greek Περσέας_ is the
   more common spelling for the mythical hero.

.. _Περσέας: https://en.wiktionary.org/wiki/%CE%A0%CE%B5%CF%81%CF%83%CE%AD%CE%B1%CF%82

.. [#] He is better known for having killed Medusa.
