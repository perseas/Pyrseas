Rules
=====

.. module:: pyrseas.dbobject.rule

The :mod:`rule` module defines two classes, :class:`Rule` and
:class:`RuleDict`, derived from :class:`DbSchemaObject` and
:class:`DbObjectDict`, respectively.

Rule
----

:class:`Rule` is derived from
:class:`~pyrseas.dbobject.DbSchemaObject` and represents a `PostgreSQL
rewrite rule
<http://www.postgresql.org/docs/current/static/rules.html>`_.

.. autoclass:: Rule

.. automethod:: Rule.identifier

.. automethod:: Rule.to_map

.. automethod:: Rule.create

.. automethod:: Rule.diff_map

Rule Dictionary
---------------

:class:`RuleDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of rewrite rules in a database.

.. autoclass:: RuleDict

.. automethod:: RuleDict.from_map

.. automethod:: RuleDict.diff_map
