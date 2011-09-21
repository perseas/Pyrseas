Constraints
===========

.. module:: pyrseas.dbobject.constraint

The :mod:`constraint` module defines six classes: :class:`Constraint`
derived from :class:`DbSchemaObject`, classes
:class:`CheckConstraint`, :class:`PrimaryKey`, :class:`ForeignKey` and
:class:`UniqueConstraint` derived from :class:`Constraint`, and
:class:`ConstraintDict` derived from :class:`DbObjectDict`.

Constraint
----------

Class :class:`Constraint` is derived from
:class:`~pyrseas.dbobject.DbSchemaObject` and represents a constraint
on a database table. Its :attr:`keylist` attributes are the schema
name, the table name and the constraint name.

.. autoclass:: Constraint

.. automethod:: Constraint.key_columns

.. automethod:: Constraint.add

.. automethod:: Constraint.drop

.. automethod:: Constraint.comment

Check Constraint
----------------

:class:`CheckConstraint` is derived from :class:`Constraint` and represents
a CHECK constraint.

.. autoclass:: CheckConstraint

.. automethod:: CheckConstraint.to_map

.. automethod:: CheckConstraint.add

.. automethod:: CheckConstraint.diff_map

Primary Key
-----------

:class:`PrimaryKey` is derived from :class:`Constraint` and represents
a primary key constraint.

.. autoclass:: PrimaryKey

.. automethod:: PrimaryKey.to_map

Foreign Key
-----------

:class:`ForeignKey` is derived from :class:`Constraint` and represents
a foreign key constraint.

The following shows a foreign key segment of a map returned by
:meth:`to_map` and expected as argument by
:meth:`ConstraintDict.diff_map` exemplifying various possibilities::

 {'t1_fgn_key1':
     {
     'columns': ['c2', 'c3'],
     'on_delete': 'restrict',
     'on_update': 'set null',
     'references':
         {'columns': ['pc2', 'pc1'], 'schema': 's1', 'table': 't2'}
     }
 }

.. autoclass:: ForeignKey

.. automethod:: ForeignKey.ref_columns

.. automethod:: ForeignKey.to_map

.. automethod:: ForeignKey.add

Unique Constraint
-----------------

:class:`UniqueConstraint` is derived from :class:`Constraint` and
represents a UNIQUE, non-primary key constraint.

.. autoclass:: UniqueConstraint

.. automethod:: UniqueConstraint.to_map

Constraint Dictionary
---------------------

Class :class:`ConstraintDict` is a dictionary derived from
:class:`~pyrseas.dbobject.DbObjectDict` and represents the collection
of constraints in a database.

.. autoclass:: ConstraintDict

.. automethod:: ConstraintDict.from_map

.. automethod:: ConstraintDict.diff_map
