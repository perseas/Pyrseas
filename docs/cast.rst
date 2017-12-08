Casts
=====

.. module:: pyrseas.dbobject.cast

The :mod:`cast` module defines two classes, :class:`Cast` and
:class:`CastDict`, derived from :class:`DbObject` and
:class:`DbObjectDict`, respectively.

Cast
----

:class:`Cast` is derived from :class:`~pyrseas.dbobject.DbObject` and
represents a `Postgres cast
<https://www.postgresql.org/docs/current/static/sql-createcast.html>`_.

A cast is identified externally as ``cast (<source_type> AS
<target_type>)``.

.. autoclass:: Cast

.. automethod:: Cast.extern_key

.. automethod:: Cast.identifier

.. automethod:: Cast.to_map

.. automethod:: Cast.create

Cast Dictionary
---------------

:class:`CastDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of casts in a database.

.. autoclass:: CastDict

.. automethod:: CastDict.from_map
