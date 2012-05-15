# -*- coding: utf-8 -*-
"""
    pyrseas.extend.denorm
    ~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: CfgAuditColumn derived from
    DbExtension and CfgAuditColumnDict derived from DbExtensionDict.
"""
from pyrseas.extend import DbExtension, DbExtensionDict
from pyrseas.extend.column import CfgColumn
from pyrseas.dbobject.column import Column
from pyrseas.dbobject import split_schema_obj


class ExtDenorms(object):
    """Helper class for defining denormalized columns"""

    def __init__(self):
        self.columns = []
        self.denorms = []

    def apply(self, table, extdb):
        currdb = extdb.current
        for col in self.columns:
            fk = self.denorms[col.denorm]._foreign_key
            reftbl = currdb.tables[(fk.ref_schema, fk.ref_table)]
            newcol = None
            for refcol in reftbl.columns:
                if refcol.name == col.basename:
                    newtype = refcol.type
                    if hasattr(col, 'type'):
                        newtype = col.type
                    newnull = None
                    if hasattr(col, 'not_null'):
                        newnull = col.not_null
                    newcol = Column(schema=table.schema, table=table.name,
                                    name=col.name, type=newtype,
                                    not_null=newnull, number=refcol.number + 1,
                                    _table=table)
                    break
            if newcol is None:
                raise KeyError("Denorm column '%s': base column '%s' not found"
                               % (col.name, self.basename))
            if col.name not in table.column_names():
                table.columns.append(newcol)

        for den in self.denorms:
            den.apply(table, extdb, self.columns)


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
        if isinstance(trans_tbl, dict) and 'single' in trans_tbl:
            strans_tbl = trans_tbl['single']
        else:
            strans_tbl = trans_tbl
        fncname = extdb.functions[func].adjust_name(strans_tbl)
        (sch, fncname) = split_schema_obj(fncname, table.schema)
        fncsig = fncname + '()'
        if (sch, fncsig) not in extdb.current.functions:
            newfunc = extdb.functions[func].apply(sch, trans_tbl, extdb)
            extdb.add_func(sch, newfunc)
            extdb.add_lang(newfunc.language)

    def apply(self, table, extdb, columns):
        """Apply copy denormalizations to the argument table.

        :param table: table to which columns/triggers will be added
        :param extdb: extension dictionaries
        :param columns: list of columns added by this denormalization
        """
        currdb = extdb.current
        fk = self._foreign_key
        reftbl = currdb.tables[(fk.ref_schema, fk.ref_table)]

        childcols = [c.name for c in columns]
        parcols = [c.basename for c in columns]
        keys = [(table.column_names()[k - 1]) for k in fk.keycols]
        parkeys = [(fk.references.column_names()[k - 1]) for k in fk.ref_cols]
        # translation table
        trans_tbls = {'single': [
                ('{{parent_schema}}', fk.ref_schema),
                ('{{parent_table}}', fk.ref_table),
                ('{{child_schema}}', table.schema),
                ('{{child_table}}', table.name)],
                      'multi': {
                'parent_key': parkeys,
                'parent_column': parcols,
                'child_fkey': keys,
                'child_column': childcols}}
        self.add_trigger_func(table, extdb, 'copy_denorm', trans_tbls)
        self.add_trigger_func(reftbl, extdb, 'copy_cascade', trans_tbls)


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
        denorms = self[(table.schema, table.name)] = ExtDenorms()

        for (i, dencol) in enumerate(indenorms):
            dentype = dencol.keys()[0]
            denspec = dencol[dentype]
            if dentype == 'copy':
                cls = ExtCopyDenormColumn
                try:
                    fkey = denspec['foreign_key']
                except KeyError as exc:
                    exc.args = ("Copy denormalization for table '%s' is "
                                "missing foreign key" % table.name, )
                    raise
                denorms.denorms.append(cls(foreign_key=fkey))
            try:
                dencols = denspec['columns']
            except KeyError as exc:
                exc.args = ("Denormalization for table '%s' has no columns"
                            % table.name, )
                raise

            args = {'denorm': i}
            for col in dencols:
                if isinstance(col, dict):
                    for fromcol in list(col.keys()):
                        args.update(basename=fromcol)
                        spec = col[fromcol]
                        if isinstance(spec, dict):
                            if 'prefix' in spec:
                                colname = spec['prefix'] + fromcol
                            elif 'suffix' in spec:
                                colname = fromcol + spec['suffix']
                        else:
                            colname = spec
                else:
                    colname = col
                    args.update(basename=colname)
                denorms.columns.append(CfgColumn(schema=table.schema,
                                           table=table.name, name=colname,
                                           **args))

    def link_current(self, constrs):
        """Connect denormalizations to actual database constraints

        :param constrs: constraints in database
        """
        for (sch, tbl) in list(self.keys()):
            for col in self[(sch, tbl)].denorms:
                if hasattr(col, 'foreign_key'):
                    fkname = col.foreign_key
                    assert(constrs[(sch, tbl, fkname)])
                    col._foreign_key = constrs[(sch, tbl, fkname)]
