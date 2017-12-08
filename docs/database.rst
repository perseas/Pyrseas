Databases
=========

.. module:: pyrseas.database

The :mod:`database` module defines class :class:`Database`.

Database
--------

A :class:`Database` can be viewed as a tree of database objects.  The
tree may have one or two main branches.  A tree with one main branch
is used by :program:`dbtoyaml` to hold the representation of the
database, as read from the Postgres catalogs.  :program:`yamltodb`
uses a second main branch to hold the representation as read from the
YAML input specification.

Each main branch consists of multiple subtrees for different kinds of
objects.  For example, the Schemas (Postgres namespaces) subtree has
all the Postgres schema objects, the Procedures subtree has all the
Postgres functions and aggregates.  The objects in the subtrees are
connected in implicit or explicit manners to related objects.  For
example, the objects in the ``schema public`` are implicitly
accessible from the corresponding :class:`Schema` object because they
all share ``public`` as the first part of their internal key (see
:meth:`DbObject.key`).  As another example, a table has explicit
links to constraints and indexes defined on it.

A :class:`Database` is initialized from a
:class:`~pyrseas.database.CatDbConnection` object (a specialized class
derived from :class:`pgdbconn.dbconn.DbConnection`).  It consists of
one or two :class:`Dicts` (the main branches in the above
discussion). A :class:`Dicts` object holds various dictionary objects
derived from :class:`~pyrseas.dbobject.DbObjectDict`, e.g.,
:class:`~pyrseas.dbobject.schema.SchemaDict`,
:class:`~pyrseas.dbobject.table.ClassDict`, and
:class:`~pyrseas.dbobject.column.ColumnDict`. The key for each
dictionary is a Python tuple (or a single value in the case of
:class:`SchemaDict` and other non-schema objects). For example, the
:class:`~pyrseas.dbobject.table.ClassDict` dictionary is indexed by
(`schema name`, `table name`)--in this context `table name` may
actually be a `sequence name`, a `view name` or a `materialized view
name`. In addition, object instances in each dictionary are linked to
related objects in other dictionaries, e.g., columns are linked to the
tables where they belong.

The :attr:`db` :class:`Dicts` object --always present-- instantiates
the database schemas, including their tables and other objects, by
querying the system catalogs.  The :attr:`ndb` :class:`Dicts` object
instantiates the schemas based on the :obj:`input_map` supplied to the
:meth:`diff_map` method.

The :meth:`to_map` method returns and the :meth:`diff_map` method
takes as input, a Python dictionary (equivalent to a YAML or JSON
object) as shown below. It uses 'schema `schema_name`' as the key for
each schema. The value corresponding to each 'schema `schema_name`' is
another dictionary using 'sequences', 'tables', etc., as keys and more
dictionaries as values. For example::

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

.. automethod:: Database.map_from_dir

.. automethod:: Database.to_map

.. automethod:: Database.diff_map
