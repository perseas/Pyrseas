Augmenter Configuration Objects
===============================

These configuration objects are predefined in the Augmenter modules or
can be defined or overriden by configuration elements in the
``augmenter`` map.  Please see also :doc:`configitems` and
:doc:`predefaug`.

.. module:: pyrseas.augment.function

Configuration Functions
-----------------------

A :class:`CfgFunction` class specifies a Postgres function to be used
by other augmenter objects.  For example, this includes procedures to
be invoked by triggers used to maintain audit columns.  The
:class:`CfgFunctionDict` class holds all the :class:`CfgFunction`
objects, indexed by the function name and its arguments.  A
:class:`CfgFunctionSource` class represents the source code for a
function or part of that source code.  A :class:`CfgFunctionTemplate`
class represents the source code for a function, which may include
other elements that can be substituted in the final result.  The class
:class:`CfgFunctionSourceDict` holds all the templates currently
defined.

.. autoclass:: CfgFunction

.. automethod:: CfgFunction.apply

.. autoclass:: CfgFunctionDict

.. automethod:: CfgFunctionDict.from_map

.. autoclass:: CfgFunctionSource

.. autoclass:: CfgFunctionTemplate

.. autoclass:: CfgFunctionSourceDict


.. module:: pyrseas.augment.column

Configuration Columns
---------------------

A :class:`CfgColumn` class defines a column to be added to a table by
other augmenter objects.  For example, this includes various columns
that serve to capture audit trail information.  The columns can be
combined in various ways by the :class:`CfgAuditColumn` objects.  The
:class:`CfgColumnDict` class holds all the :class:`CfgColumn` objects,
indexed by column name.

.. autoclass:: CfgColumn

.. automethod:: CfgColumn.apply

.. autoclass:: CfgColumnDict

.. automethod:: CfgColumnDict.from_map


.. module:: pyrseas.augment.trigger

Configuration Triggers
----------------------

A :class:`CfgTrigger` class defines a trigger to be added to a table
by other augmentation objects.  For example, this includes triggers to
maintain audit trail columns.  The :class:`CfgTriggerDict` class holds
all the :class:`CfgTrigger` objects, indexed by trigger name.

.. autoclass:: CfgTrigger

.. automethod:: CfgTrigger.apply

.. autoclass:: CfgTriggerDict

.. automethod:: CfgTriggerDict.from_map


.. module:: pyrseas.augment.audit

Configuration Audit Columns
---------------------------

A :class:`CfgAuditColumn` class defines a set of attributes (columns,
triggers) to be added to a table. The :class:`CfgAuditColumnDict`
class holds all the :class:`CfgAuditColumn` objects, indexed by
augmentation name.

.. autoclass:: CfgAuditColumn

.. automethod:: CfgAuditColumn.apply

.. autoclass:: CfgAuditColumnDict

.. automethod:: CfgAuditColumnDict.from_map
