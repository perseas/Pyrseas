Configuration Objects
=====================

These configuration objects are pre-defined in the Extender modules or
can be defined or overriden by configuration elements in the extension
map.

.. module:: pyrseas.extend.function

Configuration Function
----------------------

A :class:`CfgFunction` class specifies a function to be used by other
extension objects.  For example, this includes procedures to be
invoked by triggers used to maintain audit columns.  The
:class:`CfgFunctionDict` class holds all the :class:`CfgFunction`
objects, indexed by the function name and its arguments.

.. autoclass:: CfgFunction

.. automethod:: CfgFunction.apply

.. autoclass:: CfgFunctionDict

.. automethod:: CfgFunctionDict.from_map


.. module:: pyrseas.extend.column

Configuration Column
--------------------

A :class:`CfgColumn` class defines a column to be added to a table by
other extension objects.  For example, this includes various columns
that serve to capture audit trail information.  The columns can be
combined in various ways by the :class:`CfgAuditColumn` objects.  The
:class:`CfgColumnDict` class holds all the :class:`CfgColumn` objects,
indexed by column name.

.. autoclass:: CfgColumn

.. automethod:: CfgColumn.apply

.. autoclass:: CfgColumnDict

.. automethod:: CfgColumnDict.from_map


.. module:: pyrseas.extend.trigger

Configuration Trigger
---------------------

A :class:`CfgTrigger` class defines a trigger to be added to a table
by other extension objects.  For example, this includes triggers to
maintain audit trail columns.  The :class:`CfgTriggerDict` class holds
all the :class:`CfgTrigger` objects, indexed by trigger name.

.. autoclass:: CfgTrigger

.. automethod:: CfgTrigger.apply

.. autoclass:: CfgTriggerDict

.. automethod:: CfgTriggerDict.from_map


.. module:: pyrseas.extend.audit

Configuration Audit Columns
---------------------------

A :class:`CfgAuditColumn` class defines a set of attributes (columns,
triggers) to be added to a table. The :class:`CfgAuditColumnDict`
class holds all the :class:`CfgAuditColumn` objects, indexed by
extension name.

.. autoclass:: CfgAuditColumn

.. automethod:: CfgAuditColumn.apply

.. autoclass:: CfgAuditColumnDict

.. automethod:: CfgAuditColumnDict.from_map
