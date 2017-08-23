# -*- coding: utf-8 -*-
"""
    pyrseas.augment.column
    ~~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: CfgColumn derived from
    DbAugment and CfgColumnDict derived from DbAugmentDict.
"""
from pyrseas.augment import DbAugmentDict, DbAugment
from pyrseas.dbobject.column import Column


class CfgColumn(DbAugment):
    "A configuration column definition"

    keylist = ['name']

    def apply(self, table):
        """Add columns to the table passed in.

        :param table: table to which the columns will be added
        """
        if self.name in table.column_names():
            for col in table.columns:
                if col.name == self.name:
                    col.type = self.type
                    if hasattr(self, 'not_null'):
                        col.not_null = self.not_null
                    if hasattr(self, 'default'):
                        col.default = self.default
        else:
            dct = self.__dict__.copy()
            dct.pop('name')
            dct.pop('type')
            newcol = Column(self.name, table.schema, table.name, 0, self.type,
                            **dct)
            newcol._table = table
            table.columns.append(newcol)


class CfgColumnDict(DbAugmentDict):
    "The collection of configuration columns"

    cls = CfgColumn

    def __init__(self, config):
        self.col_trans_tbl = []
        for col in config:
            if not 'name' in config[col]:
                config[col]['name'] = col
            self[col] = CfgColumn(**config[col])
            self.col_trans_tbl.append(('{{%s}}' % col, self[col].name))

    def from_map(self, incols):
        """Initialize the dictionary of columns by converting the input dict

        :param incols: YAML dictionary defining the columns
        """
        renames = False
        for col in incols:
            if col in self:
                ccol = self[col]
            else:
                self[col] = ccol = CfgColumn(name=col)
            for attr, val in list(incols[col].items()):
                setattr(ccol, attr, val)
                if attr == 'name':
                    renames = True
        if renames:
            self.col_trans_tbl = [('{{%s}}' % col, self[col].name)
                                  for col in self]
