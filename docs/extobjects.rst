Extension Objects
=================

These objects are defined in the `ext_map` argument to the `apply`
method of :class:`~pyrseas.extenddb.ExtendDatabase`.  They tie the
desired extensions, e.g., audit columns, to the tables to be affected,
and the schemas owning the tables.

.. module:: pyrseas.extend.schema

Extension Schema
----------------

.. autoclass:: ExtSchema

.. automethod:: ExtSchema.apply

.. autoclass:: ExtSchemaDict

.. automethod:: ExtSchemaDict.from_map

.. automethod:: ExtSchemaDict.link_current

.. automethod:: ExtSchemaDict.link_refs


.. module:: pyrseas.extend.table

Extension Table
---------------

.. autoclass:: ExtDbClass

.. autoclass:: ExtTable

.. automethod:: ExtTable.apply

.. autoclass:: ExtClassDict

.. automethod:: ExtClassDict.from_map

.. automethod:: ExtClassDict.link_current
