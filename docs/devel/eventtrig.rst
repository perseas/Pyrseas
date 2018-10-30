Event Triggers
==============

.. module:: pyrseas.dbobject.eventtrig

The :mod:`eventtrig` module defines two classes, :class:`EventTrigger` and
:class:`EventTriggerDict`, derived from :class:`DbObject` and
:class:`DbObjectDict`, respectively.

Event Trigger
--------------

:class:`EventTrigger` is derived from
:class:`~pyrseas.dbobject.DbObject` and represents an `event trigger
<https://www.postgresql.org/docs/current/static/event-triggers.html>`_
available from Postgres 9.3 onwards.

.. autoclass:: EventTrigger

.. automethod:: EventTrigger.to_map

.. automethod:: EventTrigger.create

Event Trigger Dictionary
------------------------

:class:`EventTriggerDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of event triggers in a database.

.. autoclass:: EventTriggerDict

.. automethod:: EventTriggerDict.from_map
