Triggers
========

.. module:: pyrseas.dbobject.trigger

The :mod:`trigger` module defines two classes, :class:`Trigger` and
:class:`TriggerDict`, derived from :class:`DbSchemaObject` and
:class:`DbObjectDict`, respectively.

Trigger
-------

:class:`Trigger` is derived from
:class:`~pyrseas.dbobject.DbSchemaObject` and represents a Postgres
`regular or constraint trigger
<https://www.postgresql.org/docs/current/static/sql-createtrigger.html>`_.

.. autoclass:: Trigger

.. automethod:: Trigger.identifier

.. automethod:: Trigger.to_map

.. automethod:: Trigger.create

Trigger Dictionary
------------------

:class:`TriggerDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of triggers in a database.

.. autoclass:: TriggerDict

.. automethod:: TriggerDict.from_map
