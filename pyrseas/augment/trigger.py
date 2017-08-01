# -*- coding: utf-8 -*-
"""
    pyrseas.augment.trigger
    ~~~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: CfgTrigger derived from
    DbAugment and CfgTriggerDict derived from DbAugmentDict.
"""
from pyrseas.augment import DbAugmentDict, DbAugment
from pyrseas.dbobject import split_schema_obj
from pyrseas.dbobject.trigger import Trigger


class CfgTrigger(DbAugment):
    "A configuration trigger definition"

    keylist = ['name']

    def apply(self, table):
        """Create a trigger for the table passed in.

        :param table: table on which the trigger will be created
        """
        newtrg = Trigger(self.name, table.schema, table.name,
                         getattr(self, 'description', None),
                         self.procedure, self.timing, self.level, self.events)
        newtrg._iscfg = True
        if newtrg.name.startswith('{{table_name}}'):
            newtrg.name = newtrg.name.replace(newtrg.name[:14], table.name)
        newtrg._table = table
        if not hasattr(table, 'triggers'):
            table.triggers = {}
        if hasattr(newtrg, 'procedure'):
            if newtrg.procedure.startswith('{{table_name}}'):
                newtrg.procedure = newtrg.procedure.replace(
                    newtrg.procedure[:14], table.name)
            (sch, fnc) = split_schema_obj(newtrg.procedure)
            if sch != table.schema:
                newtrg.procedure = "%s.%s" % (table.schema, fnc)
        table.triggers.update({newtrg.name: newtrg})


class CfgTriggerDict(DbAugmentDict):
    "The collection of configuration triggers"

    cls = CfgTrigger

    def __init__(self, config):
        """Initialize internal configuration triggers"""
        for trg in config:
            self[trg] = CfgTrigger(**config[trg])

    def from_map(self, intrigs):
        """Initialize the dictionary of triggers by converting the input dict

        :param intrigs: YAML dictionary defining the triggers
        """
        for trg in intrigs:
            if trg in self:
                ctrg = self[trg]
            else:
                self[trg] = ctrg = CfgTrigger(name=trg)
            for attr, val in list(intrigs[trg].items()):
                setattr(ctrg, attr, val)
