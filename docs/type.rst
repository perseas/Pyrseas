Types and Domains
=================

.. module:: pyrseas.dbobject.dbtype

The :mod:`dbtype` module defines six classes, :class:`DbType` derived
from :class:`DbSchemaObject`, :class:`BaseType`, :class:`Composite`,
:class:`Enum` and :class:`Domain` derived from :class:`DbType`, and
:class:`TypeDict` derived from and :class:`DbObjectDict`.

Database Type
-------------

Class :class:`DbType` is derived from
:class:`~pyrseas.dbobject.DbSchemaObject` and represents a SQL type or
domain as defined in the PostgreSQL `pg_type` catalog. Note: Only
enumerated types are implemented currently.

.. autoclass:: DbType

Base Type
---------

:class:`BaseType` is derived from :class:`~pyrseas.dbobject.DbType`
and represents a PostgreSQL `user-defined base type
<http://www.postgresql.org/docs/current/static/xtypes.html>`_.

The map returned by :meth:`to_map` and expected as argument by
:meth:`diff_map` has the following structure (not all fields need be
present)::

  {'type t1':
      {'alignment': 'double',
       'analyze': 'analyze_func',
       'input': 'input_func',
       'internallength': 'variable',
       'output': 'output_func',
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
<http://www.postgresql.org/docs/current/static/rowtypes.html>`_.

.. autoclass:: Composite

.. automethod:: Composite.to_map

.. automethod:: Composite.create

.. automethod:: Composite.diff_map

Enum
----

:class:`Enum` is derived from :class:`~pyrseas.dbobject.DbType` and
represents an `enumerated type
<http://www.postgresql.org/docs/current/static/datatype-enum.html>`_.

.. autoclass:: Enum

.. automethod:: Enum.create

Domain
------

:class:`Domain` is derived from :class:`~pyrseas.dbobject.DbType` and
represents a domain.

.. autoclass:: Domain

.. automethod:: Domain.to_map

.. automethod:: Domain.create

Type Dictionary
---------------

:class:`TypeDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of domains and enums in a database.

.. autoclass:: TypeDict

.. automethod:: TypeDict.from_map

.. automethod:: TypeDict.link_refs

.. automethod:: TypeDict.diff_map
