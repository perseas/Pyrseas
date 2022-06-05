# -*- coding: utf-8 -*-
"""
    pyrseas.augment.audit
    ~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: CfgAuditColumn derived from
    DbAugment and CfgAuditColumnDict derived from DbAugmentDict.
"""
from pyrseas.augment import DbAugment, DbAugmentDict
from pyrseas.dbobject import split_schema_obj


class CfgAuditColumn(DbAugment):
    """An augmentation that adds automatically maintained audit columns"""

    keylist = ['name']

    def apply(self, table, augdb):
        """Apply audit columns to argument table.

        :param table: table to which columns/triggers will be added
        :param augdb: augment dictionaries
        """
        currdb = augdb.current
        sch = table.schema
        for col in self.columns:
            augdb.columns[col].apply(table)
        if hasattr(self, 'triggers'):
            for trg in self.triggers:
                augdb.triggers[trg].apply(table)
                for newtrg in table.triggers:
                    fncsig = table.triggers[newtrg].procedure
                    (sch, fnc) = split_schema_obj(fncsig, table.schema)
                    if (sch, fncsig) not in currdb.functions:
                        newfunc = augdb.functions[fnc].apply(
                            sch, augdb.columns.col_trans_tbl, augdb)
                        # add new function to the current db
                        augdb.add_func(sch, newfunc)
                        augdb.add_lang(newfunc.language)


class CfgAuditColumnDict(DbAugmentDict):
    "The collection of audit column augmentations"

    cls = CfgAuditColumn

    def __init__(self, config):
        for aud in config:
            self[aud] = CfgAuditColumn(name=aud, **config[aud])

    def from_map(self, inaudcols):
        """Initialize the dictionary of functions by converting the input map

        :param inaudcols: YAML map defining the audit column configuration
        """
        for aud in inaudcols:
            audcol = CfgAuditColumn(name=aud)
            for attr in inaudcols[aud]:
                if attr == 'columns':
                    audcol.columns = [col for col in inaudcols[aud][attr]]
                elif attr == 'triggers':
                    audcol.triggers = [col for col in inaudcols[aud][attr]]
            self[audcol.name] = audcol
