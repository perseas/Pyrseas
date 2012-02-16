# -*- coding: utf-8 -*-
"""
    pyrseas.extend.audit
    ~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: CfgAuditColumn derived from
    DbExtension and CfgAuditColumnDict derived from DbExtensionDict.
"""
from pyrseas.extend import DbExtension, DbExtensionDict
from pyrseas.dbobject.language import Language


CFG_AUDIT_COLUMNS = \
    {
    'default': {
            'columns': ['modified_by_user', 'modified_timestamp'],
            'triggers': ['audit_columns_default']
            },
    'created_date_only': {
            'columns': ['created_date']
            }
    }


class CfgAuditColumn(DbExtension):
    """An extension that adds automatically maintained audit columns"""

    keylist = ['name']

    def apply(self, table, cfgdb, db):
        """Apply configuration audit columns to argument table.

        :param table: table to which columns/triggers will be added
        :param cfgdb: configuration database
        :param db: current database catalogs
        """
        sch = table.schema
        for col in self.columns:
            cfgdb.columns[col].apply(table)
        if hasattr(self, 'triggers'):
            for trg in self.triggers:
                cfgdb.triggers[trg].apply(table)
                for newtrg in table.triggers:
                    fncsig = table.triggers[newtrg].procedure
                    fnc = fncsig[:fncsig.find('(')]
                    if (sch, fncsig) not in db.functions:
                        newfunc = cfgdb.functions[fnc].apply(
                            sch, cfgdb.columns.col_trans_tbl)
                        # add new function to the ProcDict
                        db.functions[(sch, newfunc.name)] = newfunc
                        if not hasattr(db.schemas[sch], 'functions'):
                            db.schemas[sch].functions = {}
                        # link the function to its schema
                        db.schemas[sch].functions.update(
                            {newfunc.name: newfunc})
                        if newfunc.language not in db.languages:
                            db.languages[newfunc.language] = Language(
                                name=newfunc.language)


class CfgAuditColumnDict(DbExtensionDict):
    "The collection of regular and aggregate functions in a database"

    cls = CfgAuditColumn

    def __init__(self):
        for aud in CFG_AUDIT_COLUMNS:
            self[aud] = CfgAuditColumn(name=aud, **CFG_AUDIT_COLUMNS[aud])

    def from_map(self, inaudcols):
        """Initalize the dictionary of functions by converting the input map

        :param inaudcols: YAML map defining the audit column configuration
        """
        for aud in inaudcols.keys():
            audcol = CfgAuditColumn(name=aud)
            for attr in inaudcols[aud].keys():
                if attr == 'columns':
                    audcol.columns = [col for col in inaudcols[aud][attr]]
                elif attr == 'triggers':
                    audcol.triggers = {}
                    for trg in inaudcols[aud][attr].keys():
                        audcol.triggers.update(inaudcols[aud][attr][trg])
            self[audcol.name] = audcol
