Operator Classes
================

.. module:: pyrseas.dbobject.operclass

The :mod:`operclass` module defines two classes: class
:class:`OperatorClass` derived from :class:`DbSchemaObject` and class
:class:`OperatorClassDict` derived from :class:`DbObjectDict`.

Operator Class
--------------

:class:`OperatorClass` is derived from :class:`DbSchemaObject` and
represents a `PostgreSQL operator class
<http://www.postgresql.org/docs/current/static/sql-createopclass.html>`_.

.. autoclass:: OperatorClass

.. automethod:: OperatorClass.extern_key

.. automethod:: OperatorClass.identifier

.. automethod:: OperatorClass.to_map

.. automethod:: OperatorClass.create

Operator Class Dictionary
-------------------------

:class:`OperatorClassDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of operator classes in a database.

.. autoclass:: OperatorClassDict

.. automethod:: OperatorClassDict.from_map

.. automethod:: OperatorClassDict.diff_map
