Tables, Views and Sequences
===========================

.. module:: pyrseas.dbobject.table

The :mod:`table` module defines five classes, :class:`DbClass` derived
from :class:`DbSchemaObject`, classes :class:`Sequence`,
:class:`Table` and :class:`View` derived from :class:`DbClass`, and
:class:`ClassDict`, derived from :class:`DbObjectDict`.

Database Class
--------------

Class :class:`DbClass` is derived from
:class:`~pyrseas.dbobject.DbSchemaObject` and represents a table, view
or sequence as defined in the PostgreSQL `pg_class` catalog.

.. autoclass:: DbClass

.. automethod:: DbClass.diff_description

Sequence
--------

Class :class:`Sequence` is derived from :class:`DbClass` and
represents a sequence generator. Its :attr:`keylist` attributes are
the schema name and the sequence name.

A :class:`Sequence` has the following attributes: :attr:`start_value`,
:attr:`increment_by`, :attr:`max_value`, :attr:`min_value` and
:attr:`cache_value`.

The map returned by :meth:`to_map` and expected as argument by
:meth:`diff_map` has the following structure::

  {'sequence seq1':
      {'start_value': 1,
       'increment_by': 1,
       'max_value': None,
       'min_value': None,
       'cache_value': 1
      }
  }

Only the inner dictionary is passed to :meth:`diff_map`.  The values
are defaults so in practice an empty dictionary is also acceptable.

.. autoclass:: Sequence

.. automethod:: Sequence.get_attrs

.. automethod:: Sequence.to_map

.. automethod:: Sequence.create

.. automethod:: Sequence.add_owner

.. automethod:: Sequence.diff_map

Table
-----

Class :class:`Table` is derived from :class:`DbClass` and represents a
database table. Its :attr:`keylist` attributes are the schema name and
the table name.

The map returned by :meth:`to_map` and expected as argument by
:meth:`diff_map` has a structure similar to the following::

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

.. automethod:: Table.diff_map

View
----

Class :class:`View` is derived from :class:`DbClass` and represents a
database view. Its :attr:`keylist` attributes are the schema name and
the view name.

The map returned by :meth:`to_map` and expected as argument by
:meth:`diff_map` has a structure similar to the following::

  {'view v1':
      {'definition': " SELECT ...;",
       'description': "this is the comment for view v1"
      }
  }


.. autoclass:: View

.. automethod:: View.create

.. automethod:: View.diff_map


Class Dictionary
----------------

Class :class:`ClassDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict` and represents the collection
of tables, views and sequences in a database.

.. autoclass:: ClassDict

.. automethod:: ClassDict.from_map

.. automethod:: ClassDict.link_refs

.. automethod:: ClassDict.diff_map
