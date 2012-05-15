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

    def apply(self, extdb):
        """Apply extensions to tables in a schema.

        :param extdb: the extension dictionaries
        """
        currtbl = extdb.current.tables[self.current.key()]
        if hasattr(self, 'denorms'):
            self.denorms.apply(currtbl, extdb)
        elif hasattr(self, 'audit_columns'):
            extdb.auditcols[self.audit_columns].apply(currtbl, extdb)


class ExtClassDict(DbExtensionDict):
    "The collection of tables and similar objects in a database"

    cls = ExtDbClass

    def from_map(self, schema, inobjs, extdb):
        """Initalize the dictionary of tables by converting the input map

        :param schema: schema owning the tables
        :param inobjs: YAML map defining the schema objects
        :param extdb: collection of dictionaries defining the extensions
        """
        for k in list(inobjs.keys()):
            (objtype, spc, key) = k.partition(' ')
            if spc != ' ' or objtype not in ['table']:
                raise KeyError("Unrecognized object type: %s" % k)
            if objtype == 'table':
                self[(schema.name, key)] = table = ExtTable(
                    schema=schema.name, name=key)
                intable = inobjs[k]
                if not intable:
                    raise ValueError("Table '%s' has no specification" % k)
                for attr in list(intable.keys()):
                    if attr == 'audit_columns':
                        setattr(table, attr, intable[attr])
                    elif attr == 'denorm_columns':
                        extdb.denorms.from_map(table, intable[attr])
                    else:
                        raise KeyError("Unrecognized attribute '%s' for %s"
                                       % (attr, k))
            else:
                raise KeyError("Unrecognized object type: %s" % k)

    def link_refs(self, extdenorms):
        """Connect columns to their respective tables

        :param extdenorms: dictionary of columns
        """
        for (sch, tbl) in list(extdenorms.keys()):
            if (sch, tbl) in self:
                assert isinstance(self[(sch, tbl)], ExtTable)
                self[(sch, tbl)].denorms = extdenorms[(sch, tbl)]
                for col in extdenorms[(sch, tbl)].columns:
                    col._table = self[(sch, tbl)]

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
