Conversions
===========

.. module:: pyrseas.dbobject.conversion

The :mod:`conversion` module defines two classes, :class:`Conversion`
and :class:`ConversionDict`, derived from :class:`DbSchemaObject` and
:class:`DbObjectDict`, respectively.

Conversion
----------

:class:`Conversion` is derived from
:class:`~pyrseas.dbobject.DbSchemaObject` and represents a `PostgreSQL
conversion between character set encodings
<http://www.postgresql.org/docs/current/static/sql-createconversion.html>`_.

.. autoclass:: Conversion

.. automethod:: Conversion.create

.. automethod:: Conversion.diff_map

Conversion Dictionary
---------------------

:class:`ConversionDict` is derived from
:class:`~pyrseas.dbobject.DbObjectDict`. It is a dictionary that
represents the collection of conversions in a database.

.. autoclass:: ConversionDict

.. automethod:: ConversionDict.from_map

.. automethod:: ConversionDict.diff_map
