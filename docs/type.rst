Types and Domains
=================

.. module:: pyrseas.dbobject.dbtype

The :mod:`dbtype` module defines seven classes, :class:`DbType`
derived from :class:`DbSchemaObject`, :class:`BaseType`,
:class:`Composite`, :class:`Enum`, :class:`Domain` and :class:`Range`
derived from :class:`DbType`, and :class:`TypeDict` derived from and
:class:`DbObjectDict`.

Database Type
-------------

Class :class:`DbType` is derived from
:class:`~pyrseas.dbobject.DbSchemaObject` and represents a SQL type or
domain as defined in the Postgres `pg_type` catalog.

.. autoclass:: DbType

Base Type
---------

:class:`BaseType` is derived from :class:`~pyrseas.dbobject.DbType`
and represents a Postgres `user-defined base type
<https://www.postgresql.org/docs/current/static/xtypes.html>`_.

The map returned by :meth:`to_map` and expected as argument by
:meth:`TypeDict.from_map` has the following structure (not all fields
need be present)::

  {'type t1':
      {'alignment': 'double',
       'analyze': 'analyze_func',
       'category': 'U',
       'delimiter': ',',
       'input': 'input_func',
       'internallength': 'variable',
       'output': 'output_func',
       'preferred': 'true',
       'receive': 'receive_func',
       'send': 'send_func',
       'storage': 'plain'
       'typmod_in': 'typmod_in_func',
       'typmod_out': 'typmod_out_func'
      }
  }

.. autoclass:: BaseType

.. automethod:: BaseType.to_map

.. automethod:: BaseType.create

.. automethod:: BaseType.drop

Composite
---------

:class:`Composite` is derived from :class:`~pyrseas.dbobject.DbType`
and represents a standalone `composite type
<https://www.postgresql.org/docs/current/static/rowtypes.html>`_.

.. autoclass:: Composite

.. automethod:: Composite.to_map

.. automethod:: Composite.create

.. automethod:: Composite.alter

Enum
----

:class:`Enum` is derived from :class:`~pyrseas.dbobject.DbType` and
represents an `enumerated type
<https://www.postgresql.org/docs/current/static/datatype-enum.html>`_.

.. autoclass:: Enum

.. automethod:: Enum.create

Domain
------

:class:`Domain` is derived from :class:`~pyrseas.dbobject.DbType` and
represents a `domain
<https://www.postgresql.org/docs/current/static/sql-createdomain.html>`_.

.. autoclass:: Domain

.. automethod:: Domain.to_map

.. automethod:: Domain.create

Range
-----

:class:`Range` is derived from :class:`~pyrseas.dbobject.DbType` and
represents a `Postgres range type
<https://www.postgresql.org/docs/current/static/rangetypes.html>`_.

.. autoclass:: Range

.. automethod:: Range.to_map

.. automethod:: Range.create

.. automethod:: Range.alter

Type Dictionary
---------------

:class:`TypeDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of domains and enums in a database.

.. autoclass:: TypeDict

.. automethod:: TypeDict.from_map
