Functions
=========

.. module:: pyrseas.dbobject.function

The :mod:`function` module defines four classes: class :class:`Proc`
derived from :class:`DbSchemaObject`, classes :class:`Function` and
:class:`Aggregate` derived from :class:`Proc`, and class
:class:`ProcDict` derived from :class:`DbObject`.

Procedure
---------

Class :class:`Proc` is derived from
:class:`~pyrseas.dbobject.DbSchemaObject` and represents a regular or
aggregate function.

.. autoclass:: Proc

.. automethod:: Proc.extern_key

.. automethod:: Proc.identifier

Function
--------

:class:`Function` is derived from :class:`Proc` and represents a
`PostgreSQL user-defined function
<http://www.postgresql.org/docs/current/static/xfunc.html>`_.


.. autoclass:: Function

.. automethod:: Function.to_map

.. automethod:: Function.create

.. automethod:: Function.diff_map

Aggregate Function
------------------

:class:`Aggregate` is derived from :class:`Proc` and represents a
`PostgreSQL user-defined aggregate function
<http://www.postgresql.org/docs/current/static/sql-createaggregate.html>`_.

.. autoclass:: Aggregate

.. automethod:: Aggregate.to_map

.. automethod:: Aggregate.create

.. automethod:: Aggregate.diff_map

Procedure Dictionary
--------------------

:class:`ProcDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of regular and aggregate functions in a
database.

.. autoclass:: ProcDict

.. automethod:: ProcDict.from_map

.. automethod:: ProcDict.diff_map
