Text Search Objects
===================

.. module:: pyrseas.dbobject.textsearch

The :mod:`textsearch` module defines two classes: class
:class:`TSParser` derived from :class:`DbSchemaObject` and class
:class:`TSParserDict` derived from :class:`DbObjectDict`.

Text Search Parser
------------------

:class:`TSParser` is derived from :class:`DbSchemaObject` and
represents a `PostgreSQL text search parser
<http://www.postgresql.org/docs/current/static/sql-createtsparser.html>`_.

.. autoclass:: TSParser

.. automethod:: TSParser.create

Text Search Parser Dictionary
-----------------------------

:class:`TSParserDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of text search parsers in a database.

.. autoclass:: TSParserDict

.. automethod:: TSParserDict.from_map

.. automethod:: TSParserDict.diff_map
