# -*- coding: utf-8 -*-
"""
    pyrseas.extend.table
    ~~~~~~~~~~~~~~~~~~~~

    This module defines three classes: ExtDbClass derived from
    DbExtension, ExtTable derived from ExtDbClass, and ExtClassDict
    derived from DbExtensionDict.
"""
from pyrseas.extend import DbExtensionDict, DbExtension


class ExtDbClass(DbExtension):
    """A table, sequence or view"""

    keylist = ['schema', 'name']


class ExtTable(ExtDbClass):
    """A database table definition"""

    def apply(self, db, cfgdb):
        """Apply extensions to tables in a schema.

        :param db: the database to be extended
        :param cfgdb: the configuration objects
        """
        if hasattr(self, 'audit_columns'):
            cfgdb.auditcols[self.audit_columns].apply(
                db.tables[self.current.key()], cfgdb, db)


class ExtClassDict(DbExtensionDict):
    "The collection of tables and similar objects in a database"

    cls = ExtDbClass

    def from_map(self, schema, inobjs):
        """Initalize the dictionary of tables by converting the input map

        :param schema: schema owning the tables
        :param inobjs: YAML map defining the schema objects
        """
        for k in list(inobjs.keys()):
            (objtype, spc, key) = k.partition(' ')
            if spc != ' ' or objtype not in ['table', 'sequence', 'view']:
                raise KeyError("Unrecognized object type: %s" % k)
            if objtype == 'table':
                self[(schema.name, key)] = table = ExtTable(
                    schema=schema.name, name=key)
                intable = inobjs[k]
                if not intable:
                    raise ValueError("Table '%s' has no specification" % k)
                if 'audit_columns' in intable:
                    table.audit_columns = intable['audit_columns']
            else:
                raise KeyError("Unrecognized object type: %s" % k)

    def link_current(self, tables):
        """Connect tables to be extended to actual database tables

        :param tables: tables in current schema
        """
        for (sch, tbl) in list(self.keys()):
            if not (sch, tbl) in tables:
                raise KeyError("Table %s.%s not in current database" % (
                        sch, tbl))
            if not hasattr(self[(sch, tbl)], 'current'):
                self[(sch, tbl)].current = tables[(sch, tbl)]
