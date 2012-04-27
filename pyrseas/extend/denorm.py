# -*- coding: utf-8 -*-
"""
    pyrseas.extend.denorm
    ~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: CfgAuditColumn derived from
    DbExtension and CfgAuditColumnDict derived from DbExtensionDict.
"""
from pyrseas.extend import DbExtension, DbExtensionDict
from pyrseas.dbobject.column import Column
from pyrseas.dbobject import split_schema_obj


class ExtDenormColumn(DbExtension):
    """An extension that adds automatically maintained denormalized columns"""

    keylist = ['schema', 'table']


class ExtCopyDenormColumn(ExtDenormColumn):
    """An extension that copies columns from one table to another"""

    def add_trigger_func(self, table, extdb, func, trans_tbl):
        """Add trigger, function and language, if needed

        :param table: table to which trigger will be added
        :param extdb: extension dictionaries
        :param func: base function name
        :param trans_tbl: translation table for function source
        """
        extdb.triggers[func].apply(table)
        fncname = extdb.functions[func].adjust_name(trans_tbl)
        (sch, fncname) = split_schema_obj(fncname, table.schema)
        fncsig = fncname + '()'
        if (sch, fncsig) not in extdb.current.functions:
            newfunc = extdb.functions[func].apply(sch, trans_tbl)
            extdb.schemas[sch].add_func(newfunc)
            extdb.add_lang(newfunc.language)

    def apply(self, table, extdb):
        """Apply copy denormalizations to the argument table.

        :param table: table to which columns/triggers will be added
        :param extdb: extension dictionaries
        """
        currdb = extdb.current
        fk = self._foreign_key
        reftbl = currdb.tables[(fk.ref_schema, fk.ref_table)]
        newcol = None
        for col in reftbl.columns:
            if col.name == self.copy:
                newtype = col.type
                if hasattr(self, 'type'):
                    newtype = self.type
                newnull = None
                if hasattr(col, 'not_null'):
                    newnull = col.not_null
                newcol = Column(schema=self.schema, table=self.table,
                                name=self.name, type=newtype, not_null=newnull,
                                number=col.number + 1, _table=table)
                break
        if newcol is None:
            raise KeyError("Denorm column '%s': copy column '%s' not found" %
                           (self.name, self.copy))
        if self.name not in table.column_names():
            table.columns.append(newcol)

        keys = [(table.column_names()[k - 1]) for k in fk.keycols]
        parkeys = [(fk.references.column_names()[k - 1]) for k in fk.ref_cols]
        # translation table
        trans_tbl = [
            ('{{parent_schema}}', fk.ref_schema),
            ('{{parent_table}}', fk.ref_table),
            ('{{parent_column}}', self.copy),
            ('{{parent_key}}', parkeys[0]),
            ('{{child_schema}}', table.schema),
            ('{{child_table}}', table.name),
            ('{{child_column}}', self.name),
            ('{{child_fkey}}', keys[0])]

        self.add_trigger_func(table, extdb, 'copy_denorm', trans_tbl)
        self.add_trigger_func(reftbl, extdb, 'copy_cascade', trans_tbl)


class ExtDenormDict(DbExtensionDict):
    "The collection of denormalized column extensions"

    cls = ExtDenormColumn

    def from_map(self, table, indenorms):
        """Initalize the dictionary of denormalizations from the input map

        :param table: table owning the columns
        :param indenorms: YAML map defining the denormalized columns
        """
        if not isinstance(indenorms, list):
            raise ValueError("Table %s: denorm columns must be a list" %
                             table.name)
        dencols = self[(table.schema, table.name)] = []

        for col in indenorms:
            for den in list(col.keys()):
                arg = col[den]
                if 'copy' in arg:
                    cls = ExtCopyDenormColumn
                dencols.append(cls(schema=table.schema, table=table.name,
                                   name=den, **arg))

    def link_current(self, constrs):
        """Connect denormalizations to actual database constraints

        :param constrs: constraints in database
        """
        for (sch, tbl) in list(self.keys()):
            for i, col in enumerate(self[(sch, tbl)]):
                if hasattr(col, 'foreign_key'):
                    fkname = col.foreign_key
                    assert(constrs[(sch, tbl, fkname)])
                    self[(sch, tbl)][i]._foreign_key = constrs[(
                            sch, tbl, fkname)]
