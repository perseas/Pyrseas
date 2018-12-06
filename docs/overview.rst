.. -*- coding: utf-8 -*-

Overview
========


Pyrseas provides utilities to maintain a `PostgreSQL
<https://www.postgresql.org/>`_ database schema by incrementally 
upgrading the schema.

See :doc:`user/gettingstarted` for a concrete example of how this might work.

Tools
----------

:doc:`user/command-line/dbtoyaml`
    Exports the database structure (tables, functions, etc) to a yaml file.*

:doc:`user/command-line/yamltodb`
    Incrementally upgrades the target database using the desired schema in the yaml file.

:doc:`user/advanced/dbaugment` 
    Modifies the \*.yaml files to add the same column/trigger/etc to every table.

:doc:`user/advanced/datacopy` 
   Populates tables in the database from your \*.csv files.

:doc:`user/advanced/preactions` 
    Runs SQL files in a folder for complex migration scenarios.

\* Multiple yaml files is also supported, see `--multiple-files` in :doc:`user/command-line/dbtoyaml`


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
