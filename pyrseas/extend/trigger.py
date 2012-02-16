# -*- coding: utf-8 -*-
"""
    pyrseas.extend.trigger
    ~~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: CfgTrigger derived from
    DbExtension and CfgTriggerDict derived from DbExtensionDict.
"""
from pyrseas.extend import DbExtensionDict, DbExtension
from pyrseas.dbobject.trigger import Trigger


CFG_TRIGGERS = \
    {
    'audit_columns_default':
        {
        'name': '{{table_name}}_20_aud_dflt',
        'events': ['update'],
        'level': 'row',
        'procedure': 'aud_dflt()',
        'timing': 'before'}
    }


class CfgTrigger(DbExtension):
    "A configuration trigger definition"

    keylist = ['name']

    def apply(self, table):
        """Create a trigger for the table passed in.

        :param table: table on which the trigger will be created
        """
        newtrg = Trigger(schema=table.schema, table=table.name,
                         **self.__dict__)
        if newtrg.name.startswith('{{table_name}}'):
            newtrg.name = newtrg.name.replace(newtrg.name[:14], table.name)
        newtrg._table = table
        if not hasattr(table, 'triggers'):
            table.triggers = {}
        table.triggers.update({newtrg.name: newtrg})


class CfgTriggerDict(DbExtensionDict):
    "The collection of configuration triggers"

    cls = CfgTrigger

    def __init__(self):
        """Initialize internal configuration triggers"""
        for trg in CFG_TRIGGERS:
            self[trg] = CfgTrigger(**CFG_TRIGGERS[trg])

    def from_map(self, intrigs):
        """Initialize the dictionary of triggers by converting the input dict

        :param intrigs: YAML dictionary defining the triggers
        """
        for trg in intrigs:
            if trg in self:
                ctrg = self[trg]
            else:
                self[trg] = ctrg = CfgTrigger(name=trg)
            for attr, val in intrigs[trg].items():
                setattr(ctrg, attr, val)
