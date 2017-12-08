Operators
=========

.. module:: pyrseas.dbobject.operator

The :mod:`operator` module defines two classes: class
:class:`Operator` derived from :class:`DbSchemaObject` and class
:class:`OperatorDict` derived from :class:`DbObjectDict`.

Operator
---------

:class:`Operator` is derived from :class:`DbSchemaObject` and
represents a `Postgres user-defined operator
<https://www.postgresql.org/docs/current/static/xoper.html>`_.

.. autoclass:: Operator

.. automethod:: Operator.extern_key

.. automethod:: Operator.qualname

.. automethod:: Operator.identifier

.. automethod:: Operator.create

Operator Dictionary
-------------------

:class:`OperatorDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of operators in a database.

.. autoclass:: OperatorDict

.. automethod:: OperatorDict.from_map
