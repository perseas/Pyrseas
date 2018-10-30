Augmentation Objects
====================

These objects are defined in the `aug_map` argument to the `apply`
method of :class:`~pyrseas.augmentdb.AugmentDatabase`.  They tie the
desired augmentations, e.g., audit columns, to the tables to be
affected, and the schemas owning the tables.

.. module:: pyrseas.augment.schema

Augmentation Schema
-------------------

.. autoclass:: AugSchema

.. automethod:: AugSchema.apply

.. autoclass:: AugSchemaDict

.. automethod:: AugSchemaDict.from_map

.. automethod:: AugSchemaDict.link_current

.. automethod:: AugSchemaDict.link_refs


.. module:: pyrseas.augment.table

Augmentation Table
------------------

.. autoclass:: AugDbClass

.. autoclass:: AugTable

.. automethod:: AugTable.apply

.. autoclass:: AugClassDict

.. automethod:: AugClassDict.from_map

.. automethod:: AugClassDict.link_current
