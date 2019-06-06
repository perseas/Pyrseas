Database Connections
====================

.. module:: pyrseas.lib.dbconn

The :mod:`dbconn` module defines :class:`DbConnection`.

Database Connection
-------------------

A :class:`DbConnection` is a helper class representing a connection to
a `Postgres <http://www.postgresql.org>`_ database via the `Psycopg
<http://initd.org/psycopg/>`_ adapter.  It provides an easier
interface than direct access to Psycopg.  For example::

 >>> from pyrseas.lib.dbconn import DbConnection
 >>> db = DbConnection('dbname')
 >>> db.fetchone("SHOW server_version")[0]
 >>> db.commit()

A :class:`DbConnection` is not necessarily connected when created.

.. autoclass:: DbConnection

.. automethod:: DbConnection.connect

.. automethod:: DbConnection.close

.. automethod:: DbConnection.commit

.. automethod:: DbConnection.rollback

.. automethod:: DbConnection.execute

.. automethod:: DbConnection.fetchone

.. automethod:: DbConnection.fetchall

.. automethod:: DbConnection.copy_to

.. automethod:: DbConnection.copy_from

.. automethod:: DbConnection.sql_copy_to
