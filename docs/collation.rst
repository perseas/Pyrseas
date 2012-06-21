Collations
==========

.. module:: pyrseas.dbobject.collation

The :mod:`collation` module defines two classes, :class:`Collation`
and :class:`CollationDict`, derived from :class:`DbSchemaObject` and
:class:`DbObjectDict`, respectively.

Collation
---------

:class:`Collation` is derived from
:class:`~pyrseas.dbobject.DbSchemaObject` and represents a `PostgreSQL
collation
<http://www.postgresql.org/docs/current/static/collation.html>`_
(available on PostgreSQL 9.1 or later).

.. autoclass:: Collation

.. automethod:: Collation.create

Collation Dictionary
--------------------

:class:`CollationDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of collations in a database.

.. autoclass:: CollationDict

.. automethod:: CollationDict.from_map

.. automethod:: CollationDict.diff_map
