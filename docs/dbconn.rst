Database Connections
====================

.. module:: pyrseas.dbconn

The :mod:`dbconn` module defines :class:`DbConnection`.

Database Connection
-------------------

A :class:`DbConnection` is a helper class representing a connection to
a `PostgreSQL <http://www.postgresql.org>`_ database via the `Psycopg
<http://initd.org/psycopg/>`_ adapter.  A :class:`DbConnection` is not
necessarily connected. It will typically connect to the database when
the :class:`~pyrseas.dbobject.DbObjectDict`
:meth:`~pyrseas.dbobject.DbObjectDict.fetch` method is first
invoked. It is normally disconnected just before the
:class:`~pyrseas.database.Database`
:meth:`~pyrseas.database.Database.from_catalog` returns.

.. autoclass:: DbConnection

.. automethod:: DbConnection.connect

.. automethod:: DbConnection.fetchone

.. automethod:: DbConnection.fetchall

.. autoattribute:: DbConnection.version
