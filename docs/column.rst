Columns
=======

.. module:: pyrseas.dbobject.column

The :mod:`column` module defines two classes, :class:`Column` derived
from :class:`DbSchemaObject` and :class:`ColumnDict`, derived from
:class:`DbObjectDict`.

Column
------

:class:`Column` is derived from
:class:`~pyrseas.dbobject.DbSchemaObject` and represents a column in a
table, or an attribute in a composite type.  Its :attr:`keylist`
attributes are the schema name and the table name.

A :class:`Column` has the following attributes: :attr:`name`,
:attr:`type`, :attr:`not_null` and :attr:`default`. The :attr:`number`
attribute is also present but is not made visible externally.

.. autoclass:: Column

.. automethod:: Column.to_map

.. automethod:: Column.add

.. automethod:: Column.add_privs

.. automethod:: Column.diff_privileges

.. automethod:: Column.comment

.. automethod:: Column.drop

.. automethod:: Column.rename

.. automethod:: Column.set_sequence_default

.. automethod:: Column.diff_map

Column Dictionary
-----------------

Class :class:`ColumnDict` is a dictionary derived from
:class:`~pyrseas.dbobject.DbObjectDict` and represents the collection
of columns in a database, across multiple tables. It is indexed by the
schema name and table name, and each value is a list of
:class:`Column` objects.

.. autoclass:: ColumnDict

.. automethod:: ColumnDict.from_map
