Databases
=========

.. module:: pyrseas.database

The :mod:`database` module defines :class:`Database`.

Database
--------

A :class:`Database` is initialized from a
:class:`~pyrseas.database.CatDbConnection` object (a specialized class
derived from :class:`~pyrseas.lib.dbconn.DbConnection`).
It consists of one or
two :class:`Dicts`. A :class:`Dicts` object holds various dictionary
objects derived from :class:`~pyrseas.dbobject.DbObjectDict`, e.g.,
:class:`~pyrseas.dbobject.schema.SchemaDict`,
:class:`~pyrseas.dbobject.table.ClassDict`, and
:class:`~pyrseas.dbobject.column.ColumnDict`. The key for each dictionary is a
Python tuple (or a single value in the case of
:class:`SchemaDict`). For example, the
:class:`~pyrseas.dbobject.table.ClassDict` dictionary is indexed by (`schema
name`, `table name`). In addition, object instances in each dictionary
are linked to related objects in other dictionaries, e.g., columns are
linked to the tables where they belong.

The :attr:`db` :class:`Dicts` object --always present-- defines the
database schemas, including their tables and other objects, by
querying the system catalogs.  The :attr:`ndb` :class:`Dicts` object
defines the schemas based on the :obj:`input_map` supplied to the
:meth:`diff_map` method.

The :meth:`to_map` method returns and the :meth:`diff_map` method
takes as input, a dictionary as shown below. It uses 'schema
`schema_name`' as the key for each schema. The value corresponding to
each 'schema `schema_name`' is another dictionary using 'sequences',
'tables', etc., as keys and more dictionaries as values. For example::

  {'schema public':
      {'sequence seq1': { ... },
       'sequence seq2': { ... },
       'table t1': { ... },
       'table t2': { ... },
       'table t3': { ... },
       'view v1': { ... }
      },
   'schema s1': { ... },
   'schema s2': { ... }
  }

Refer to :class:`~pyrseas.dbobject.table.Sequence`,
:class:`~pyrseas.dbobject.table.Table` and
:class:`~pyrseas.dbobject.table.View` for details on the lower level
dictionaries.

.. autoclass:: Database

Methods :meth:`from_catalog` and :meth:`from_map` are for internal
use. Methods :meth:`to_map` and :meth:`diff_map` are the external API.

.. automethod:: Database.from_catalog

.. automethod:: Database.from_map

.. automethod:: Database.to_map

.. automethod:: Database.diff_map
