Text Search Objects
===================

.. module:: pyrseas.dbobject.textsearch

The :mod:`textsearch` module defines eight classes: classes
:class:`TSConfiguration`, :class:`TSDictionary`, :class:`TSParser` and
:class:`TSTemplate` derived from :class:`DbSchemaObject`, and classes
:class:`TSConfigurationDict`, :class:`TSDictionaryDict`,
:class:`TSParserDict` and :class:`TSTemplateDict` derived from
:class:`DbObjectDict`.

Text Search Configuration
-------------------------

:class:`TSConfiguration` is derived from :class:`DbSchemaObject` and
represents a `PostgreSQL text search configuration
<http://www.postgresql.org/docs/current/static/sql-createtsconfig.html>`_.

.. autoclass:: TSConfiguration

.. automethod:: TSConfiguration.to_map

.. automethod:: TSConfiguration.create

Text Search Configuration Dictionary
------------------------------------

:class:`TSConfigurationDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of text search configurations in a database.

.. autoclass:: TSConfigurationDict

.. automethod:: TSConfigurationDict.from_map

.. automethod:: TSConfigurationDict.diff_map

Text Search Dictionary
----------------------

:class:`TSDictionary` is derived from :class:`DbSchemaObject` and
represents a `PostgreSQL text search dictionary
<http://www.postgresql.org/docs/current/static/textsearch-dictionaries.html>`_.

.. autoclass:: TSDictionary

.. automethod:: TSDictionary.create

Text Search Dictionary Dictionary
---------------------------------

:class:`TSDictionaryDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a Python dictionary
that represents the collection of text search dictionaries in a
database.

.. autoclass:: TSDictionaryDict

.. automethod:: TSDictionaryDict.from_map

.. automethod:: TSDictionaryDict.diff_map

Text Search Parser
------------------

:class:`TSParser` is derived from :class:`DbSchemaObject` and
represents a `PostgreSQL text search parser
<http://www.postgresql.org/docs/current/static/sql-createtsparser.html>`_.

.. autoclass:: TSParser

.. automethod:: TSParser.create

Text Search Parser Dictionary
-----------------------------

:class:`TSParserDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of text search parsers in a database.

.. autoclass:: TSParserDict

.. automethod:: TSParserDict.from_map

.. automethod:: TSParserDict.diff_map

Text Search Template
--------------------

:class:`TSTemplate` is derived from :class:`DbSchemaObject` and
represents a `PostgreSQL text search template
<http://www.postgresql.org/docs/current/static/sql-createtstemplate.html>`_.

.. autoclass:: TSTemplate

.. automethod:: TSTemplate.create

Text Search Template Dictionary
-------------------------------

:class:`TSTemplateDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of text search templates in a database.

.. autoclass:: TSTemplateDict

.. automethod:: TSTemplateDict.from_map

.. automethod:: TSTemplateDict.diff_map
