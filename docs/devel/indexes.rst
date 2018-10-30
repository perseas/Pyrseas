Indexes
=======

.. module:: pyrseas.dbobject.index

The :mod:`index` module defines two classes, :class:`Index` and
:class:`IndexDict`, derived from :class:`DbSchemaObject` and
:class:`DbObjectDict`, respectively.

Index
-----

Class :class:`Index` is derived from
:class:`~pyrseas.dbobject.DbSchemaObject` and represents an index on a
database table, other than a primary key or unique constraint
index. Its :attr:`keylist` attributes are the schema name, the table
name and the index name.  Note that index names are supposed to be
unique with a given schema so the table name doesn't have to be part
of the :attr:`keylist`, but has been retained to facilitate certain
operations.

.. autoclass:: Index

.. automethod:: Index.key_expressions

.. automethod:: Index.to_map

.. automethod:: Index.create

.. automethod:: Index.alter

.. automethod:: Index.drop

Index Dictionary
----------------

Class :class:`IndexDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict` and represents the collection
of indexes in a database.

.. autoclass:: IndexDict

.. automethod:: IndexDict.from_map
