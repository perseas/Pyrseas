# -*- coding: utf-8 -*-
"""
    pyrseas.augment.column
    ~~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: CfgColumn derived from
    DbAugment and CfgColumnDict derived from DbAugmentDict.
"""
from pyrseas.augment import DbAugmentDict, DbAugment
from pyrseas.dbobject.column import Column


CFG_COLUMNS = \
    {
    'created_by_user': {'not_null': True, 'type': 'character varying(63)'},
    'created_by_ip_addr': {'not_null': True, 'type': 'inet'},
    'created_date': {'default': "('now'::text)::date", 'not_null': True,
                     'type': 'date'},
    'created_timestamp': {'not_null': True,
                          'type': 'timestamp with time zone'},
    'modified_by_ip_addr': {'not_null': True, 'type': 'inet'},
    'modified_by_user': {'not_null': True, 'type': 'character varying(63)'},
    'modified_timestamp': {'not_null': True,
                           'type': 'timestamp with time zone'}
    }


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
            newcol = Column(schema=table.schema, table=table.name,
                            **self.__dict__)
            newcol.number = 0
            newcol._table = table
            table.columns.append(newcol)


class CfgColumnDict(DbAugmentDict):
    "The collection of configuration columns"

    cls = CfgColumn

    def __init__(self):
        self.col_trans_tbl = []
        for col in CFG_COLUMNS:
            if not 'name' in CFG_COLUMNS[col]:
                CFG_COLUMNS[col]['name'] = col
            self[col] = CfgColumn(**CFG_COLUMNS[col])
            self.col_trans_tbl.append(('{{%s}}' % col, self[col].name))

    def from_map(self, incols):
        """Initialize the dictionary of columns by converting the input dict

        :param incols: YAML dictionary defining the columns
        """
        for col in incols:
            if col in self:
                ccol = self[col]
            else:
                self[col] = ccol = CfgColumn(name=col)
            for attr, val in list(incols[col].items()):
                setattr(ccol, attr, val)
