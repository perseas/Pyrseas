Extender Databases
==================

.. module:: pyrseas.extenddb

The :mod:`extenddb` module defines :class:`ExtendDatabase`.

Extender Database
-----------------

An :class:`ExtendDatabase` is derived from
:class:`~pyrseas.database.Database`.  It contains two "dictionaries"
objects.

One is the :class:`Dicts` container from its parent class. The `db`
Dicts object, defines the database schemas, including their tables and
other objects, by querying the system catalogs.

The second container is a :class:`ExtDicts` object.  The `edb`
ExtDicts object defines the extension schemas and extension
configuration objects based on the `ext_map` supplied to the `apply`
method.  The configuration objects may be supplied either by other
Extender modules or from the 'extender' configuration tree on the
`ext_map` supplied to the `apply` method.

.. autoclass:: ExtendDatabase

.. automethod:: ExtendDatabase.apply

.. automethod:: ExtendDatabase.from_extmap
