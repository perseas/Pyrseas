Foreign Data Objects
====================

.. module:: pyrseas.dbobject.foreign

The :mod:`foreign` module defines six classes: classes
:class:`ForeignDataWrapper`, :class:`ForeignServer` and
:class:`UserMapping` derived from :class:`DbObject`, and classes
:class:`ForeignDataWrapperDict`, :class:`ForeignServerDict` and
:class:`UserMappingDict` derived from :class:`DbObjectDict`.

Foreign Data Wrapper
--------------------

:class:`ForeignDataWrapper` is derived from :class:`DbObject` and
represents a `PostgreSQL foreign data wrapper
<http://www.postgresql.org/docs/current/static/sql-createcreateforeigndatawrapper.html>`_.
For PostgreSQL versions 9.1 and later see also `Foreign Data
<http://www.postgresql.org/docs/current/static/ddl-foreign-data.html>`_
and `Writing A Foreign Data Wrapper
<http://www.postgresql.org/docs/current/static/fdwhandler.html>`_.

.. autoclass:: ForeignDataWrapper

.. automethod:: ForeignDataWrapper.create

Foreign Data Wrapper Dictionary
-------------------------------

:class:`ForeignDataWrapperDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of foreign data wrappers in a database.

.. autoclass:: ForeignDataWrapperDict

.. automethod:: ForeignDataWrapperDict.from_map

.. automethod:: ForeignDataWrapperDict.to_map

.. automethod:: ForeignDataWrapperDict.diff_map

Foreign Server
--------------

:class:`ForeignServer` is derived from :class:`DbObject` and
represents a `PostgreSQL foreign server
<http://www.postgresql.org/docs/current/static/sql-createserver.html>`_.

.. autoclass:: ForeignServer

.. automethod:: ForeignServer.create

Foreign Server Dictionary
-------------------------

:class:`ForeignServerDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`.  It is a Python dictionary
that represents the collection of foreign servers in a database.

.. autoclass:: ForeignServerDict

.. automethod:: ForeignServerDict.from_map

.. automethod:: ForeignServerDict.to_map

.. automethod:: ForeignServerDict.diff_map

User Mapping
------------

:class:`UserMapping` is derived from :class:`DbObject` and represents
a `PostgreSQL user mapping of a user to a foreign server
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
