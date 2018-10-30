Augmenter Databases
===================

.. module:: pyrseas.augmentdb

The :mod:`augmentdb` module defines the class :class:`AugmentDatabase`.

Augmenter Database
------------------

An :class:`AugmentDatabase` is derived from
:class:`~pyrseas.database.Database`.  It contains two "dictionary"
objects.

One is the :class:`Dicts` container from its parent class. The `db`
Dicts object, defines the database schemas, including their tables and
other objects, by querying the system catalogs.

The second container is an :class:`AugDicts` object.  The `adb`
AugDicts object specifies the schemas to be augmented and the
augmenter configuration objects.  The latter objects may be supplied
either by other Augmenter modules or from the ``augmenter``
configuration tree on the `aug_map` supplied to the :meth:`apply`
method.

.. autoclass:: AugmentDatabase

.. automethod:: AugmentDatabase.apply

.. automethod:: AugmentDatabase.from_augmap
