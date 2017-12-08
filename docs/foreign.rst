Foreign Data Objects
====================

.. module:: pyrseas.dbobject.foreign

The :mod:`foreign` module defines nine classes related to Postgres
foreign data wrappers (FDWs), namely: :class:`DbObjectWithOptions`
derived from :class:`DbObject`, classes :class:`ForeignDataWrapper`,
:class:`ForeignServer` and :class:`UserMapping` derived from
:class:`DbObjectWithOptions`, :class:`ForeignTable` derived from
:class:`DbObjectWithOptions` and :class:`Table`, classes
:class:`ForeignDataWrapperDict`, :class:`ForeignServerDict` and
:class:`UserMappingDict` derived from :class:`DbObjectDict`, and
:class:`ForeignTableDict` derived from :class:`ClassDict`.

Database Object With Options
----------------------------

:class:`DbObjectWithOptions` is derived from
:class:`~pyrseas.dbobject.DbObject`.  It is a helper class for dealing
with the OPTIONS clauses common to the foreign data objects.

.. autoclass:: DbObjectWithOptions

.. automethod:: DbObjectWithOptions.to_map

.. automethod:: DbObjectWithOptions.options_clause

.. automethod:: DbObjectWithOptions.diff_options

.. automethod:: DbObjectWithOptions.alter

Foreign Data Wrapper
--------------------

:class:`ForeignDataWrapper` is derived from `DbObjectWithOptions` and
represents a `Postgres foreign data wrapper
<https://www.postgresql.org/docs/current/static/sql-createforeigndatawrapper.html>`_.
See also `Foreign Data
<https://www.postgresql.org/docs/current/static/ddl-foreign-data.html>`_
and `Writing A Foreign Data Wrapper
<https://www.postgresql.org/docs/current/static/fdwhandler.html>`_.

.. autoclass:: ForeignDataWrapper

.. automethod:: ForeignDataWrapper.to_map

.. automethod:: ForeignDataWrapper.create

Foreign Data Wrapper Dictionary
-------------------------------

:class:`ForeignDataWrapperDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of foreign data wrappers in a database.

.. autoclass:: ForeignDataWrapperDict

.. automethod:: ForeignDataWrapperDict.from_map

Foreign Server
--------------

:class:`ForeignServer` is derived from :class:`DbObjectWithOptions`
and represents a `Postgres foreign server
<https://www.postgresql.org/docs/current/static/sql-createserver.html>`_.

.. autoclass:: ForeignServer

.. automethod:: ForeignServer.identifier

.. automethod:: ForeignServer.to_map

.. automethod:: ForeignServer.create

Foreign Server Dictionary
-------------------------

:class:`ForeignServerDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`.  It is a Python dictionary
that represents the collection of foreign servers in a database.

.. autoclass:: ForeignServerDict

.. automethod:: ForeignServerDict.from_map

.. automethod:: ForeignServerDict.to_map

User Mapping
------------

:class:`UserMapping` is derived from :class:`DbObjectWithOptions` and
represents a `mapping of a Postgres user to a foreign server
<https://www.postgresql.org/docs/current/static/sql-createusermapping.html>`_.

.. autoclass:: UserMapping

.. automethod:: UserMapping.extern_key

.. automethod:: UserMapping.identifier

.. automethod:: UserMapping.create

User Mapping Dictionary
-----------------------

:class:`UserMappingDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`.  It is a dictionary that
represents the collection of user mappings in a database.

.. autoclass:: UserMappingDict

.. automethod:: UserMappingDict.from_map

.. automethod:: UserMappingDict.to_map

Foreign Table
-------------

:class:`ForeignTable` is derived from :class:`DbObjectWithOptions` and
:class:`~pyrseas.dbobject.table.Table`.  It represents a `Postgres
foreign table
<https://www.postgresql.org/docs/current/static/sql-createforeigntable.html>`_.

.. autoclass:: ForeignTable

.. automethod:: ForeignTable.to_map

.. automethod:: ForeignTable.create

.. automethod:: ForeignTable.drop

Foreign Table Dictionary
------------------------

:class:`ForeignTableDict` is derived from
:class:`~pyrseas.dbobject.table.ClassDict`.  It is a dictionary that
represents the collection of foreign tables in a database.

.. autoclass:: ForeignTableDict

.. automethod:: ForeignTableDict.from_map
