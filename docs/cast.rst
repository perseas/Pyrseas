Casts
=====

.. module:: pyrseas.dbobject.cast

The :mod:`cast` module defines two classes, :class:`Cast` and
:class:`CastDict`, derived from :class:`DbObject` and
:class:`DbObjectDict`, respectively.

Cast
----

:class:`Cast` is derived from :class:`~pyrseas.dbobject.DbObject` and
represents a `PostgreSQL cast
<http://www.postgresql.org/docs/current/static/sql-createcast.html>`_.

.. autoclass:: Cast

.. automethod:: Cast.extern_key

.. automethod:: Cast.identifier

.. automethod:: Cast.to_map

.. automethod:: Cast.create

.. automethod:: Cast.diff_map

Cast Dictionary
---------------

:class:`CastDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of casts in a database.

.. autoclass:: CastDict

.. automethod:: CastDict.to_map

.. automethod:: CastDict.from_map

.. automethod:: CastDict.diff_map
