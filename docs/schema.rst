Schemas
=======

.. module:: pyrseas.dbobject.schema

The :mod:`schema` module defines two classes, :class:`Schema` and
:class:`SchemaDict`, derived from :class:`DbObject` and
:class:`DbObjectDict`, respectively.

Schema
------

:class:`Schema` is derived from :class:`~pyrseas.dbobject.DbObject`
and represents a database schema or Postgres namespace, i.e., a
collection of tables and other objects. The 'public' schema is
currently treated specially as in most contexts an unqualified object
is assumed to be part of it, e.g., table "t" is usually shorthand for
table "public.t."  The 'pyrseas' schema, if present, is excluded as it
is only intended for use by :program:`dbaugment` or other Pyrseas
internal purposes.

.. autoclass:: Schema

.. automethod:: Schema.extern_dir

.. automethod:: Schema.to_map

.. automethod:: Schema.create

.. automethod:: Schema.drop

.. automethod:: Schema.data_import

Schema Dictionary
-----------------

:class:`SchemaDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of schemas in a database. Certain internal
schemas (information_schema, pg_catalog, etc.) owned by the 'postgres'
user are excluded.

.. autoclass:: SchemaDict

Method :meth:`from_map` is called from :class:`Database`
:meth:`~pyrseas.database.Database.from_map` to start a recursive
interpretation of the input map. The :obj:`inmap` argument is the same
as input to the :meth:`~pyrseas.database.Database.diff_map` method of
:class:`Database`. The :obj:`newdb` argument is the holder of
:class:`~pyrseas.dbobject.DbObjectDict`-derived dictionaries which is
filled in as the recursive interpretation proceeds.

.. automethod:: SchemaDict.from_map

.. automethod:: SchemaDict.to_map

.. automethod:: SchemaDict.data_import
