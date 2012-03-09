Foreign Data Objects
====================

.. module:: pyrseas.dbobject.foreign

The :mod:`foreign` module defines nine classes:
:class:`DbObjectWithOptions` derived from :class:`DbObject`, classes
:class:`ForeignDataWrapper`, :class:`ForeignServer` and
:class:`UserMapping` derived from :class:`DbObjectWithOptions`,
:class:`ForeignTable` derived from :class:`DbObjectWithOptions` and
:class:`Table`, classes :class:`ForeignDataWrapperDict`,
:class:`ForeignServerDict` and :class:`UserMappingDict` derived from
:class:`DbObjectDict`, and :class:`ForeignTableDict` derived from
:class:`ClassDict`.

Database Object With Options
----------------------------

:class:`DbObjectWithOptions` is derived from
:class:`~pyrseas.dbobject.DbObject`.  It is a helper function dealing
with the OPTIONS clauses common to the foreign data objects.

.. autoclass:: DbObjectWithOptions

.. automethod:: DbObjectWithOptions.options_clause

.. automethod:: DbObjectWithOptions.diff_options

.. automethod:: DbObjectWithOptions.diff_map

Foreign Data Wrapper
--------------------

:class:`ForeignDataWrapper` is derived from
:class:`DbObjectWithOptions` and represents a `PostgreSQL foreign data
wrapper
<http://www.postgresql.org/docs/current/static/sql-createcreateforeigndatawrapper.html>`_.
For PostgreSQL versions 9.1 and later see also `Foreign Data
<http://www.postgresql.org/docs/current/static/ddl-foreign-data.html>`_
and `Writing A Foreign Data Wrapper
<http://www.postgresql.org/docs/current/static/fdwhandler.html>`_.

.. autoclass:: ForeignDataWrapper

.. automethod:: ForeignDataWrapper.to_map

.. automethod:: ForeignDataWrapper.create

.. automethod:: ForeignDataWrapper.diff_map

Foreign Data Wrapper Dictionary
-------------------------------

:class:`ForeignDataWrapperDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of foreign data wrappers in a database.

.. autoclass:: ForeignDataWrapperDict

.. automethod:: ForeignDataWrapperDict.from_map

.. automethod:: ForeignDataWrapperDict.link_refs

.. automethod:: ForeignDataWrapperDict.to_map

.. automethod:: ForeignDataWrapperDict.diff_map

Foreign Server
--------------

:class:`ForeignServer` is derived from :class:`DbObjectWithOptions`
and represents a `PostgreSQL foreign server
<http://www.postgresql.org/docs/current/static/sql-createserver.html>`_.

.. autoclass:: ForeignServer

.. automethod:: ForeignServer.identifier

.. automethod:: ForeignServer.to_map

.. automethod:: ForeignServer.create

.. automethod:: ForeignServer.diff_map

Foreign Server Dictionary
-------------------------

:class:`ForeignServerDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`.  It is a Python dictionary
that represents the collection of foreign servers in a database.

.. autoclass:: ForeignServerDict

.. automethod:: ForeignServerDict.from_map

.. automethod:: ForeignServerDict.to_map

.. automethod:: ForeignServerDict.link_refs

.. automethod:: ForeignServerDict.diff_map

User Mapping
------------

:class:`UserMapping` is derived from :class:`DbObjectWithOptions` and
represents a `PostgreSQL user mapping of a user to a foreign server
<http://www.postgresql.org/docs/current/static/sql-createusermapping.html>`_.

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

.. automethod:: UserMappingDict.diff_map

Foreign Table
-------------

:class:`ForeignTable` is derived from :class:`DbObjectWithOptions` and
:class:`~pyrseas.dbobject.table.Table`.  It represents a `PostgreSQL foreign
table
<http://www.postgresql.org/docs/current/static/sql-createforeigntable.html>`_
(available on PostgreSQL 9.1 or later).

.. autoclass:: ForeignTable

.. automethod:: ForeignTable.to_map

.. automethod:: ForeignTable.create

.. automethod:: ForeignTable.drop

.. automethod:: ForeignTable.diff_map

Foreign Table Dictionary
------------------------

:class:`ForeignTableDict` is derived from
:class:`~pyrseas.dbobject.table.ClassDict`.  It is a dictionary that
represents the collection of foreign tables in a database.

.. autoclass:: ForeignTableDict

.. automethod:: ForeignTableDict.from_map

.. automethod:: ForeignTableDict.link_refs

.. automethod:: ForeignTableDict.diff_map
