.. -*- coding: utf-8 -*-

Overview
========

Pyrseas provides a framework and utilities to create, upgrade and
maintain a `PostgreSQL <http://www.postgresql.org/>`_ database.  Its
purpose is to enhance and follow through on the concepts of the
`Andromeda Project <http://www.andromeda-project.org/>`_.

Whereas Andromeda expects the database designer or developer to
provide a single `YAML <http://yaml.org/>`_ specification file of the
database to be created, Pyrseas allows the development database to be
created using the familar SQL CREATE statements.  The developer can
then run the `dbtoyaml` utility to generate the YAML specification from
the database.  The spec can then be stored in any desired VCS
repository.  Similarly, she can add columns or modify tables or other
objects using SQL ALTER statements and regenerate the YAML spec with
dbtoyaml.

When ready to create or upgrade a test or production database, the
`yamltodb` utility can be used with the YAML spec as input, to generate
a script of SQL CREATE or ALTER statements to modify the database so
that it matches the input spec.

Andromeda also uses the YAML specification to generate a PHP-based
application to maintain the database tables.  Pyrseas `dbappgen`
utility will allow a secondary YAML spec to generate a Python-based
administrative application for database maintenance, which can be
activated using `dbapprun`.

Use Cases
---------

The following two sections discuss the main scenarios where Pyrseas
tools may be helpful. The first deals with the problem of controlling
database structural changes while the second examines the topic of
repetitive database maintenance operations.

Version Control
---------------

The case for implementing a tool to facilitate version control over
SQL databases was made in a couple of blog posts: `Version
Control, Part 1: Pre-SQL
<http://pyrseas.wordpress.com/2011/02/01/version-control-part-i-pre-sql/>`_
and `Version Control, Part 2: SQL Databases
<http://pyrseas.wordpress.com/2011/02/07/version-control-part-2-sql-databases/>`_. In
summary, SQL data definition commands are generally incompatible with
traditional version control approaches which usually require
comparisons (diffs) between revisions of source files.

The Pyrseas version control tools are not designed to be the ultimate
SQL database version control solution. Instead, they are aimed at
assisting two or more developers or DbAs in sharing changes to the
underlying database as they implement a database application. The
sharing can occur through a centralized or distributed VCS. The
Pyrseas tools may even be used by a single DbA in conjunction with a
distributed VCS to quickly explore alternative designs. The tools can
also help to share changes with a conventional QA team, but may
require additional controls for final releases and production
installations.

Data Maintenance
----------------

Pyrseas data administration tools (to be developed) aim to supplement
the agile database development process mentioned above. While there
are tools such as `pgAdmin III <http://www.pgadmin.org/>`_ that can be
used for routine data entry tasks, their scope of action is usually a
single table. For example, if you're entering data for a customer
invoice, you need to know (or find by querying) the customer ID. On
the other hand, `Django's admin site application
<http://docs.djangoproject.com/en/1.2/intro/tutorial02/>`_ can present
more than one table on a web page, but it requires defining the
database "model" in Python and has limitations on how the database can
be structured.

Naming
------

The project name comes from `Python <http://www.python.org/>`_, the
programming language, and `Perseas
<http://en.wikipedia.org/wiki/Perseus>`_ [#]_, the Greek mythological
hero who rescued Andromeda from a sea monster [#]_.  It is hoped that
Pyrseas will rescue the Andromeda project <grin>.  You can pronounce
Pyrseas like the hero.


.. rubric:: Footnotes

.. [#] The common English name for Perseas is Perseus and the Ancient
   Greek name is Perseos. However, in modern Greek Περσέας_ is the
   more common spelling for the mythical hero.

.. _Περσέας: http://en.wiktionary.org/wiki/%CE%A0%CE%B5%CF%81%CF%83%CE%AD%CE%B1%CF%82

.. [#] He is better known for having killed Medusa.
