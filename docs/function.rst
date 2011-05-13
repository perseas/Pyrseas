Functions
=========

.. module:: pyrseas.dbobject.function

The :mod:`function` module defines two classes, :class:`Function` and
:class:`FunctionDict`, derived from :class:`DbObject` and
:class:`DbObjectDict`, respectively.

Function
--------

:class:`Function` is derived from :class:`~pyrseas.dbobject.DbObject`
and represents a function.

.. autoclass:: Function

.. automethod:: Function.extern_key

.. automethod:: Function.identifier

.. automethod:: Function.to_map

.. automethod:: Function.create

.. automethod:: Function.diff_map

Function Dictionary
-------------------

:class:`FunctionDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of functions in a database.

.. autoclass:: FunctionDict

.. automethod:: FunctionDict.from_map

.. automethod:: FunctionDict.diff_map
