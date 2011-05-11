Procedural Languages
====================

.. module:: pyrseas.dbobject.language

The :mod:`language` module defines two classes, :class:`Language` and
:class:`LanguageDict`, derived from :class:`DbObject` and
:class:`DbObjectDict`, respectively.

Procedural Language
-------------------

:class:`Language` is derived from :class:`~pyrseas.dbobject.DbObject`
and represents a procedural language.

.. autoclass:: Language

.. automethod:: Language.to_map

.. automethod:: Language.create

.. automethod:: Language.diff_map

Language Dictionary
-------------------

:class:`LanguageDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of procedural languages in a
database. Internal languages ('internal', 'c' and 'sql') are excluded.

.. autoclass:: LanguageDict

.. automethod:: LanguageDict.from_map

.. automethod:: LanguageDict.link_refs

.. automethod:: LanguageDict.to_map

.. automethod:: LanguageDict.diff_map
