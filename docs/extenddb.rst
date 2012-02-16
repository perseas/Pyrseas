Extender Databases
==================

.. module:: pyrseas.extenddb

The :mod:`extenddb` module defines :class:`ExtendDatabase`.

Extender Database
-----------------

An :class:`ExtendDatabase` is derived from
:class:`~pyrseas.database.Database`.  Like its parent, it is
initialized with a :class:`~pyrseas.dbconn.DbConnection` object.  It
contains three "dictionaries" objects.

One is the :class:`Dicts` container from its parent class. The `db`
Dicts object, defines the database schemas, including their tables and
other objects, by querying the system catalogs.

The second container is a :class:`ExtDicts` object.  The `edb`
ExtDicts object defines the extension schemas based on the `ext_map`
supplied to the `apply` method.

The last is a :class:`CfgDicts` object.  The `cdb` CfgDicts object
defines the configuration objects supplied either by other Extender
modules or from the 'extender' configuration tree on the `ext_map`
supplied to the `apply` method.

.. autoclass:: ExtendDatabase

.. automethod:: ExtendDatabase.apply
