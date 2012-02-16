# -*- coding: utf-8 -*-
"""
    pyrseas.extend.column
    ~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: CfgColumn derived from
    DbExtension and CfgColumnDict derived from DbExtensionDict.
"""
from pyrseas.extend import DbExtensionDict, DbExtension
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


class CfgColumn(DbExtension):
    "A configuration column definition"

    keylist = ['name']

    def apply(self, table):
        """Add columns to the table passed in.

        :param table: table to which the columns will be added
        """
        newcol = Column(schema=table.schema, table=table.name, **self.__dict__)
        newcol.number = 0
        newcol._table = table
        table.columns.append(newcol)


class CfgColumnDict(DbExtensionDict):
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
            for attr, val in incols[col].items():
                setattr(ccol, attr, val)
