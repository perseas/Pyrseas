Database Objects
================

.. module:: pyrseas.dbobject

The :mod:`dbobject` module defines two low-level classes and an
intermediate class. Most Pyrseas classes are derived from either
:class:`DbObject` or :class:`DbObjectDict`.

Database Object
---------------

A :class:`DbObject` represents a database object such as a schema,
table, or column, defined in a Postgres `system catalog
<https://www.postgresql.org/docs/current/static/catalogs.html>`_. It is
initialized from a dictionary of attributes. Derived classes should
define a :attr:`keylist` that is a list of attribute names that
uniquely identify each object instance within the database.

.. autoclass:: DbObject

.. autoattribute:: DbObject.objtype

.. autoattribute:: DbObject.keylist

.. automethod:: DbObject.key

The following methods are generally used to map objects for external
output:

.. automethod:: DbObject.extern_key

.. automethod:: DbObject.query

.. automethod:: DbObject.extern_filename

.. automethod:: DbObject.identifier

.. automethod:: DbObject.to_map

.. automethod:: DbObject.map_privs

The following methods generate SQL statements from the object
properties and sometimes from a second object:

.. automethod:: DbObject.comment

.. automethod:: DbObject.alter_owner

.. automethod:: DbObject.drop

.. automethod:: DbObject.rename

.. automethod:: DbObject.alter

.. automethod:: DbObject.diff_privileges

.. automethod:: DbObject.diff_description


Database Object Dictionary
--------------------------

A :class:`DbObjectDict` represents a collection of :class:`DbObject`'s
and is derived from the Python built-in type :class:`dict`. If a
:class:`~pyrseas.lib.dbconn.DbConnection` object is used for
initialization, an internal method is called to initialize the
dictionary from the database catalogs. The :class:`DbObjectDict`
:meth:`fetch` method fetches all objects using the `query` method
defined by derived classes. Derived classes should also define a
:attr:`cls` attribute for the associated :class:`DbObject` class,
e.g., :class:`~pyrseas.schema.SchemaDict` sets :attr:`cls` to
:class:`~pyrseas.schema.Schema`.

.. autoclass:: DbObjectDict

.. autoattribute:: DbObjectDict.cls

.. automethod:: DbObjectDict.to_map

.. automethod:: DbObjectDict.fetch


Schema Object
-------------

A :class:`DbSchemaObject` is derived from :class:`DbObject`. It is
used as a base class for objects owned by a schema and to define
certain common methods. This is different from the
:class:`~pyrseas.schema.Schema` that represents the schema (Postgres
namespace) itself.

.. autoclass:: DbSchemaObject

.. automethod:: DbSchemaObject.identifier

.. automethod:: DbSchemaObject.qualname

.. automethod:: DbSchemaObject.unqualify

.. automethod:: DbSchemaObject.rename
