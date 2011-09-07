Operator Families
=================

.. module:: pyrseas.dbobject.operfamily

The :mod:`operfamily` module defines two classes: class
:class:`OperatorFamily` derived from :class:`DbSchemaObject` and class
:class:`OperatorFamilyDict` derived from :class:`DbObjectDict`.

Operator Family
---------------

:class:`OperatorFamily` is derived from :class:`DbSchemaObject` and
represents a `PostgreSQL operator family
<http://www.postgresql.org/docs/current/static/sql-createopfamily.html>`_.

.. autoclass:: OperatorFamily

.. automethod:: OperatorFamily.extern_key

.. automethod:: OperatorFamily.identifier

.. automethod:: OperatorFamily.create

Operator Family Dictionary
--------------------------

:class:`OperatorFamilyDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of operator families in a database.

.. autoclass:: OperatorFamilyDict

.. automethod:: OperatorFamilyDict.from_map

.. automethod:: OperatorFamilyDict.diff_map
