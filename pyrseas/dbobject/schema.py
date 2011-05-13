# -*- coding: utf-8 -*-
"""
    pyrseas.schema
    ~~~~~~~~~~~~~~

    This defines two classes, Schema and SchemaDict, derived from
    DbObject and DbObjectDict, respectively.
"""
from pyrseas.dbobject import DbObjectDict, DbObject
from table import Table, Sequence, View


class Schema(DbObject):
    """A database schema definition, i.e., a named collection of tables,
    views, triggers and other schema objects."""

    keylist = ['name']
    objtype = 'SCHEMA'

    def to_map(self, dbschemas):
        """Convert tables, etc., dictionaries to a YAML-suitable format

        :param dbschemas: dictionary of schemas
        :return: dictionary
        """
        key = self.extern_key()
        schema = {key: {}}
        if hasattr(self, 'sequences'):
            seqs = {}
            for seq in self.sequences.keys():
                seqs.update(self.sequences[seq].to_map())
            schema[key].update(seqs)
        if hasattr(self, 'tables'):
            tbls = {}
            for tbl in self.tables.keys():
                tbls.update(self.tables[tbl].to_map(dbschemas))
            schema[key].update(tbls)
        if hasattr(self, 'views'):
            views = {}
            for view in self.views.keys():
                views.update(self.views[view].to_map())
            schema[key].update(views)
        if hasattr(self, 'functions'):
            functions = {}
            for func in self.functions.keys():
                functions.update(self.functions[func].to_map())
            schema[key].update(functions)
        if hasattr(self, 'description'):
            schema[key].update(description=self.description)
        return schema

    def create(self):
        """Return SQL statements to CREATE the schema

        :return: SQL statements
        """
        stmts = ["CREATE SCHEMA %s" % self.name]
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts

    def diff_map(self, inschema):
        """Generate SQL to transform an existing schema

        :param inschema: a YAML map defining the new schema
        :return: list of SQL statements

        Compares the schema to an input schema and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []
        if hasattr(self, 'description'):
            if hasattr(inschema, 'description'):
                if self.description != inschema.description:
                    self.description = inschema.description
                    stmts.append(self.comment())
            else:
                del self.description
                stmts.append(self.comment())
        else:
            if hasattr(inschema, 'description'):
                self.description = inschema.description
                stmts.append(self.comment())
        return stmts


class SchemaDict(DbObjectDict):
    "The collection of schemas in a database.  Minimally, the 'public' schema."

    cls = Schema
    query = \
        """SELECT nspname AS name, description
           FROM pg_namespace n JOIN pg_roles ON (nspowner = pg_roles.oid)
                LEFT JOIN pg_description d
                     ON (n.oid = d.objoid AND d.objsubid = 0)
           WHERE nspname = 'public' OR rolname <> 'postgres'
           ORDER BY nspname"""

    def from_map(self, inmap, newdb):
        """Initialize the dictionary of schemas by converting the input map

        :param inmap: the input YAML map defining the schemas
        :param newdb: collection of dictionaries defining the database

        Starts the recursive analysis of the input map and
        construction of the internal collection of dictionaries
        describing the database objects.
        """
        for sch in inmap.keys():
            key = sch.split()[1]
            schema = self[key] = Schema(name=key)
            inschema = inmap[sch]
            intables = {}
            infuncs = {}
            for key in inschema.keys():
                if key.startswith('table ') or key.startswith('view ') \
                        or key.startswith('sequence '):
                    intables.update({key: inschema[key]})
                elif key.startswith('function '):
                    infuncs.update({key: inschema[key]})
                elif key == 'oldname':
                    schema.oldname = inschema[key]
                    del inschema['oldname']
                elif key == 'description':
                    schema.description = inschema[key]
                else:
                    raise KeyError("Expected typed object, found '%s'" % key)
            newdb.tables.from_map(schema, intables, newdb)
            newdb.functions.from_map(schema, infuncs)

    def link_refs(self, dbtables, dbfunctions):
        """Connect tables and sequences to their respective schemas

        :param dbtables: dictionary of tables, sequences and views
        :param dbfunctions: dictionary of functions

        Fills in the `tables`, `sequences`, `views` dictionaries for
        each schema by traversing the `dbtables` dictionary, which is
        keyed by schema and table name. Fills in the `functions`
        dictionary by traversing the `dbfunctions` dictionary.
        """
        for (sch, tbl) in dbtables.keys():
            table = dbtables[(sch, tbl)]
            assert self[sch]
            schema = self[sch]
            if isinstance(table, Table):
                if not hasattr(schema, 'tables'):
                    schema.tables = {}
                schema.tables.update({tbl: table})
            elif isinstance(table, Sequence):
                if not hasattr(schema, 'sequences'):
                    schema.sequences = {}
                schema.sequences.update({tbl: table})
            elif isinstance(table, View):
                if not hasattr(schema, 'views'):
                    schema.views = {}
                schema.views.update({tbl: table})
        for (sch, fnc, arg) in dbfunctions.keys():
            assert self[sch]
            schema = self[sch]
            if not hasattr(schema, 'functions'):
                schema.functions = {}
            schema.functions.update({(fnc, arg): dbfunctions[(sch, fnc, arg)]})

    def to_map(self):
        """Convert the schema dictionary to a regular dictionary

        :return: dictionary

        Invokes the `to_map` method of each schema to construct a
        dictionary of schemas.
        """
        schemas = {}
        for sch in self.keys():
            schemas.update(self[sch].to_map(self))
        return schemas

    def diff_map(self, inschemas):
        """Generate SQL to transform existing schemas

        :param input_map: a YAML map defining the new schemas
        :return: list of SQL statements

        Compares the existing schema definitions, as fetched from the
        catalogs, to the input map and generates SQL statements to
        transform the schemas accordingly.
        """
        stmts = []
        # check input schemas
        for sch in inschemas.keys():
            insch = inschemas[sch]
            # does it exist in the database?
            if sch in self:
                stmts.append(self[sch].diff_map(insch))
            else:
                # check for possible RENAME
                if hasattr(insch, 'oldname'):
                    oldname = insch.oldname
                    try:
                        stmts.append(self[oldname].rename(insch.name))
                        del self[oldname]
                    except KeyError, exc:
                        exc.args = ("Previous name '%s' for schema '%s' "
                                   "not found" % (oldname, insch.name), )
                        raise
                else:
                    # create new schema
                    stmts.append(insch.create())
        # check database schemas
        for sch in self.keys():
            # if missing and not 'public', drop it
            if sch != 'public' and sch not in inschemas:
                self[sch].dropped = True
        return stmts

    def _drop(self):
        """Actually drop the schemas

        :return: SQL statements
        """
        stmts = []
        for sch in self.keys():
            if sch != 'public' and hasattr(self[sch], 'dropped'):
                stmts.append(self[sch].drop())
        return stmts
