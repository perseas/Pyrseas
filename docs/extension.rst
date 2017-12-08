Extensions
==========

.. module:: pyrseas.dbobject.extension

The :mod:`extension` module defines two classes, :class:`Extension`
and :class:`ExtensionDict`, derived from :class:`DbObject` and
:class:`DbObjectDict`, respectively.

Extension
---------

:class:`Extension` is derived from
:class:`~pyrseas.dbobject.DbObject` and represents a `Postgres
extension
<https://www.postgresql.org/docs/current/static/extend-extensions.html>`_.

.. autoclass:: Extension

.. automethod:: Extension.create

.. automethod:: Extension.alter

Extension Dictionary
--------------------

:class:`ExtensionDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of extensions in a database.

.. autoclass:: ExtensionDict

.. automethod:: ExtensionDict.from_map
