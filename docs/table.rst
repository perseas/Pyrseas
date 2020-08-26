Tables, Views and Sequences
===========================

.. module:: pyrseas.dbobject.table

The :mod:`table` and :mod:`view` modules define six classes,
:class:`DbClass` derived from :class:`DbSchemaObject`, classes
:class:`Sequence`, :class:`Table` and :class:`View` derived from
:class:`DbClass`, :class:`MaterializedView` derived from
:class:`View`, and :class:`ClassDict`, derived from
:class:`DbObjectDict`.

Database Class
--------------

Class :class:`DbClass` is derived from
:class:`~pyrseas.dbobject.DbSchemaObject` and represents a table, view
or sequence as defined in the Postgres `pg_class` catalog.

.. autoclass:: DbClass

Sequence
--------

Class :class:`Sequence` is derived from :class:`DbClass` and
represents a `sequence generator
<https://www.postgresql.org/docs/current/static/sql-createsequence.html>`_.
Its :attr:`keylist` attributes are the schema name and the sequence
name.

The map returned by :meth:`to_map` and expected as argument by
:meth:`ClassDict.from_map` has the following structure::

  {'sequence seq1':
      {'cache_value': 1,
       'data_type': 'integer',
       'increment_by': 1,
       'max_value': None,
       'min_value': None,
       'owner_column': 'c1',
       'owner_table': 't1',
       'start_value': 1
      }
  }

.. autoclass:: Sequence

.. automethod:: Sequence.get_attrs

.. automethod:: Sequence.get_dependent_table

.. automethod:: Sequence.to_map

.. automethod:: Sequence.create

.. automethod:: Sequence.add_owner

.. automethod:: Sequence.alter

.. automethod:: Sequence.drop

Table
-----

Class :class:`Table` is derived from :class:`DbClass` and represents a
database table. Its :attr:`keylist` attributes are the schema name and
the table name.

The map returned by :meth:`to_map` and expected as argument by
:meth:`ClassDict.from_map` has a structure similar to the following::

 {'table t1':
     {'columns':
         [
         {'c1': {'type': 'integer', 'not_null': True}},
         {'c2': {'type': 'text'}},
         {'c3': {'type': 'smallint'}},
         {'c4': {'type': 'date', 'default': 'now()'}}
         ],
      'description': "this is the comment for table t1",
      'primary_key':
         {'t1_prim_key':
             {'columns': ['c1', 'c2']}
         },
      'foreign_keys':
         {'t1_fgn_key1':
             {'columns': ['c2', 'c3'],
               'references':
                   {'table': 't2', 'columns': ['pc2', 'pc1']}
             },
          't1_fgn_key2':
             {'columns': ['c2'],
              'references': {'table': 't3', 'columns': ['qc1']}
             }
         },
      'unique_constraints': {...},
      'indexes': {...}
     }
 }

The values for :obj:`unique_constraints` and :obj:`indexes` follow a
pattern similar to :obj:`primary_key`, but there can be more than one
such specification.

.. autoclass:: Table

.. automethod:: Table.column_names

.. automethod:: Table.to_map

.. automethod:: Table.create

.. automethod:: Table.drop

.. automethod:: Table.diff_options

.. automethod:: Table.alter

.. automethod:: Table.alter_drop_columns

.. automethod:: Table.data_export

.. automethod:: Table.data_import

Class Dictionary
----------------

Class :class:`ClassDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict` and represents the collection
of tables, views and sequences in a database.

.. autoclass:: ClassDict

.. automethod:: ClassDict.from_map


.. module:: pyrseas.dbobject.view

View
----

Class :class:`View` is derived from :class:`DbClass` and represents a
database view. Its :attr:`keylist` attributes are the schema name and
the view name.

The map returned by :meth:`to_map` and expected as argument by
:meth:`ClassDict.from_map` has a structure similar to the following::

  {'view v1':
      {'columns': [{'c1': {'type': 'integer'}},
                   {'c2': {'type': 'date'}}],
       'definition': " SELECT ...;",
       'description': "this is the comment for view v1"
      }
  }


.. autoclass:: View

.. automethod:: View.to_map

.. automethod:: View.create

.. automethod:: View.alter

Materialized View
-----------------

Class :class:`MaterializedView` is derived from :class:`View` and
represents a `materialized view
<https://www.postgresql.org/docs/current/static/sql-creatematerializedview.html>`_. Its
:attr:`keylist` attributes are the schema name and the view name.

.. autoclass:: MaterializedView

.. automethod:: MaterializedView.to_map

.. automethod:: MaterializedView.create
