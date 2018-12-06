
Benefits
========

The following sections discuss the main scenarios where Pyrseas
tools may be helpful.

Version Control - Database History
-----------------------------------

The case for implementing a tool to facilitate version control over
SQL databases was made in a couple of blog posts: `Version
Control, Part 1: Pre-SQL
<https://pyrseas.wordpress.com/2011/02/01/version-control-part-i-pre-sql/>`_
and `Version Control, Part 2: SQL Databases
<https://pyrseas.wordpress.com/2011/02/07/version-control-part-2-sql-databases/>`_. In
summary, SQL data definition commands are generally incompatible with
traditional version control approaches which usually require
comparisons (diffs) between revisions of source files.

A refinement of the approach described in the aforementioned blog
posts will be of interest to users with many objects in their database
schemas, i.e., many tables, views, functions, and other more complex
objects.  Instead of storing a complete database specification in a
single YAML file, by using the `--multiple-files` option to
:program:`dbtoyaml`, the specification can be broken down into files
corresponding, generally, to a single database object.  This allows a
VCS **diff** facility to easily highlight database changes.  Please
refer to the :doc:`user/command-line/dbtoyaml` and :doc:`user/command-line/yamltodb` utilities for further
details.

The Pyrseas version control tools are not designed to be the ultimate
SQL database version control solution. Instead, they are aimed at
assisting two or more developers or DBAs in sharing changes to the
underlying database as they implement a database application. The
sharing can occur through a distributed or centralized VCS. The
Pyrseas tools may even be used by a single DBA in conjunction with a
distributed VCS to quickly explore alternative designs. The tools can
also help to share changes with a conventional QA team, but may
require additional controls for final releases and production
installations.

Version Control - Branching and Merging
---------------------------------------

Pyrseas works well with version control branching and merging.  There is no
single order that database changes have to be applied, and so Pyrseas
is OK with changes being applied in a different order.

Say you have two branches, bugfix & feature.  Bugfix is adding the column "bugfix" and the
feature branch is adding the column "feature".  

1. Feature adds column "feature" to its branch (and DB).
2. Bugfix adds column "bugfix" to its branch.
3. Feature merges in the bugfix branch and therefore adds column "bugfix" (which already has column "feature").
4. Bugfix merges in Feature and adds column "feature" (which already has column "bugfix").

Each branch added the columns to their database in a different order.