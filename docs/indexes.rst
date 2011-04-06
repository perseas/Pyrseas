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
name and the index name.

An :class:`Index` has the following attributes: :attr:`access_method`,
:attr:`unique`, and :attr:`keycols`.

.. autoclass:: Index

. automethod:: Index.key_columns

. automethod:: Index.to_map

.. automethod:: Index.create

.. automethod:: Index.diff_map

Index Dictionary
----------------

Class :class:`IndexDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict` and represents the collection
of indexes in a database.

.. autoclass:: IndexDict

.. automethod:: IndexDict.from_map

.. automethod:: IndexDict.diff_map
