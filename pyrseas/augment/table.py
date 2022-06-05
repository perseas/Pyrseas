# -*- coding: utf-8 -*-
"""
    pyrseas.augment.table
    ~~~~~~~~~~~~~~~~~~~~~

    This module defines three classes: AugDbClass derived from
    DbAugment, AugTable derived from AugDbClass, and AugClassDict
    derived from DbAugmentDict.
"""
from pyrseas.augment import DbAugmentDict, DbAugment


class AugDbClass(DbAugment):
    """A table, sequence or view"""

    keylist = ['schema', 'name']


class AugTable(AugDbClass):
    """A database table definition"""

    def apply(self, augdb):
        """Augment tables in a schema.

        :param augdb: the augmenter dictionaries
        """
        currtbl = augdb.current.tables[self.current.key()]
        if hasattr(self, 'audit_columns'):
            if self.audit_columns not in augdb.auditcols:
                raise KeyError("Specification %s not in current configuration"
                               % self.audit_columns)
            augdb.auditcols[self.audit_columns].apply(currtbl, augdb)


class AugClassDict(DbAugmentDict):
    "The collection of tables and similar objects in a database"

    cls = AugDbClass

    def from_map(self, schema, inobjs, augdb):
        """Initialize the dictionary of tables by converting the input map

        :param schema: schema owning the tables
        :param inobjs: YAML map defining the schema objects
        :param augdb: collection of dictionaries defining the augmentations
        """
        for k in inobjs:
            (objtype, spc, key) = k.partition(' ')
            if spc != ' ' or objtype not in ['table']:
                raise KeyError("Unrecognized object type: %s" % k)
            if objtype == 'table':
                self[(schema.name, key)] = table = AugTable(
                    schema=schema.name, name=key)
                intable = inobjs[k]
                if not intable:
                    raise ValueError("Table '%s' has no specification" % k)
                for attr in intable:
                    if attr == 'audit_columns':
                        setattr(table, attr, intable[attr])
                    else:
                        raise KeyError("Unrecognized attribute '%s' for %s"
                                       % (attr, k))
            else:
                raise KeyError("Unrecognized object type: %s" % k)

    def link_current(self, tables):
        """Connect tables to be augmented to actual database tables

        :param tables: tables in current schema
        """
        for (sch, tbl) in self:
            if not (sch, tbl) in tables:
                raise KeyError("Table %s.%s not in current database" % (
                    sch, tbl))
            if not hasattr(self[(sch, tbl)], 'current'):
                self[(sch, tbl)].current = tables[(sch, tbl)]
