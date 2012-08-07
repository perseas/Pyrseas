# -*- coding: utf-8 -*-
"""
    pyrseas.schema
    ~~~~~~~~~~~~~~

    This defines two classes, Schema and SchemaDict, derived from
    DbObject and DbObjectDict, respectively.
"""
from pyrseas.dbobject import DbObjectDict, DbObject
from pyrseas.dbobject import quote_id, split_schema_obj, commentable, ownable
from pyrseas.dbobject.dbtype import BaseType, Composite, Domain, Enum
from pyrseas.dbobject.table import Table, Sequence, View


class Schema(DbObject):
    """A database schema definition, i.e., a named collection of tables,
    views, triggers and other schema objects."""

    keylist = ['name']
    objtype = 'SCHEMA'
    allprivs = 'UC'

    def to_map(self, dbschemas, no_owner, no_privs):
        """Convert tables, etc., dictionaries to a YAML-suitable format

        :param dbschemas: dictionary of schemas
        :param no_owner: exclude schema owner information
        :param no_privs: exclude privilege information
        :return: dictionary
        """
        key = self.extern_key()
        schema = {key: {} if no_owner else {'owner': self.owner}}

        def mapper(schema, objtypes):
            mappeddict = {}
            if hasattr(schema, objtypes):
                schemadict = getattr(schema, objtypes)
                for objkey in list(schemadict.keys()):
                    mappeddict.update(schemadict[objkey].to_map(no_owner))
            return mappeddict

        def mapper2(schema, objtypes):
            mappeddict = {}
            if hasattr(schema, objtypes):
                schemadict = getattr(schema, objtypes)
                for objkey in list(schemadict.keys()):
                    mappeddict.update(schemadict[objkey].to_map(
                            no_owner, no_privs))
            return mappeddict

        if hasattr(self, 'tables'):
            tbls = {}
            for tbl in list(self.tables.keys()):
                tbls.update(self.tables[tbl].to_map(
                        dbschemas, no_owner, no_privs))
            schema[key].update(tbls)

        for objtypes in ['conversions', 'domains',
                         'operators', 'operclasses', 'operfams',
                         'tsconfigs', 'tsdicts', 'tsparsers', 'tstempls',
                         'types', 'collations']:
            schema[key].update(mapper(self, objtypes))

        for objtypes in ['ftables', 'functions', 'sequences', 'views']:
            schema[key].update(mapper2(self, objtypes))

        if not no_privs and hasattr(self, 'privileges'):
            schema[key].update({'privileges': self.map_privs()})
        if hasattr(self, 'description'):
            schema[key].update(description=self.description)
        return schema

    @commentable
    @ownable
    def create(self):
        """Return SQL statements to CREATE the schema

        :return: SQL statements
        """
        return ["CREATE SCHEMA %s" % quote_id(self.name)]


class SchemaDict(DbObjectDict):
    "The collection of schemas in a database.  Minimally, the 'public' schema."

    cls = Schema
    query = \
        """SELECT nspname AS name, rolname AS owner,
                  array_to_string(nspacl, ',') AS privileges,
                  obj_description(n.oid, 'pg_namespace') AS description
           FROM pg_namespace n
                JOIN pg_roles r ON (r.oid = nspowner)
           WHERE nspname NOT IN ('information_schema', 'pg_toast')
                 AND nspname NOT LIKE 'pg_temp\_%'
                 AND nspname NOT LIKE 'pg_toast_temp\_%'
           ORDER BY nspname"""

    def from_map(self, inmap, newdb):
        """Initialize the dictionary of schemas by converting the input map

        :param inmap: the input YAML map defining the schemas
        :param newdb: collection of dictionaries defining the database

        Starts the recursive analysis of the input map and
        construction of the internal collection of dictionaries
        describing the database objects.
        """
        for key in list(inmap.keys()):
            (objtype, spc, sch) = key.partition(' ')
            if spc != ' ' or objtype != 'schema':
                raise KeyError("Unrecognized object type: %s" % key)
            schema = self[sch] = Schema(name=sch)
            inschema = inmap[key]
            intypes = {}
            intables = {}
            infuncs = {}
            inopers = {}
            inopcls = {}
            inopfams = {}
            inconvs = {}
            intscs = {}
            intsds = {}
            intsps = {}
            intsts = {}
            inftbs = {}
            incolls = {}
            for key in list(inschema.keys()):
                if key.startswith('domain '):
                    intypes.update({key: inschema[key]})
                elif key.startswith('type '):
                    intypes.update({key: inschema[key]})
                elif key.startswith('table ') or key.startswith('view ') \
                        or key.startswith('sequence '):
                    intables.update({key: inschema[key]})
                elif key.startswith('function ') \
                        or key.startswith('aggregate '):
                    infuncs.update({key: inschema[key]})
                elif key.startswith('operator family'):
                    inopfams.update({key: inschema[key]})
                elif key.startswith('operator class'):
                    inopcls.update({key: inschema[key]})
                elif key.startswith('operator '):
                    inopers.update({key: inschema[key]})
                elif key.startswith('conversion '):
                    inconvs.update({key: inschema[key]})
                elif key.startswith('text search dictionary '):
                    intsds.update({key: inschema[key]})
                elif key.startswith('text search template '):
                    intsts.update({key: inschema[key]})
                elif key.startswith('text search parser '):
                    intsps.update({key: inschema[key]})
                elif key.startswith('text search configuration '):
                    intscs.update({key: inschema[key]})
                elif key.startswith('foreign table '):
                    inftbs.update({key: inschema[key]})
                elif key.startswith('collation '):
                    incolls.update({key: inschema[key]})
                elif key == 'oldname':
                    schema.oldname = inschema[key]
                elif key == 'description':
                    schema.description = inschema[key]
                else:
                    raise KeyError("Expected typed object, found '%s'" % key)
            newdb.types.from_map(schema, intypes, newdb)
            newdb.tables.from_map(schema, intables, newdb)
            newdb.functions.from_map(schema, infuncs)
            newdb.operators.from_map(schema, inopers)
            newdb.operclasses.from_map(schema, inopcls)
            newdb.operfams.from_map(schema, inopfams)
            newdb.conversions.from_map(schema, inconvs)
            newdb.tsdicts.from_map(schema, intsds)
            newdb.tstempls.from_map(schema, intsts)
            newdb.tsparsers.from_map(schema, intsps)
            newdb.tsconfigs.from_map(schema, intscs)
            newdb.ftables.from_map(schema, inftbs, newdb)
            newdb.collations.from_map(schema, incolls)

    def link_refs(self, dbtypes, dbtables, dbfunctions, dbopers, dbopfams,
                  dbopcls, dbconvs, dbtsconfigs, dbtsdicts, dbtspars,
                  dbtstmpls, dbftables, dbcolls):
        """Connect types, tables and functions to their respective schemas

        :param dbtypes: dictionary of types and domains
        :param dbtables: dictionary of tables, sequences and views
        :param dbfunctions: dictionary of functions
        :param dbopers: dictionary of operators
        :param dbopfams: dictionary of operator families
        :param dbopcls: dictionary of operator classes
        :param dbconvs: dictionary of conversions
        :param dbtsconfigs: dictionary of text search configurations
        :param dbtsdicts: dictionary of text search dictionaries
        :param dbtspars: dictionary of text search parsers
        :param dbtstmpls: dictionary of text search templates
        :param dbftables: dictionary of foreign tables
        :param dbcolls: dictionary of collations

        Fills in the `domains` dictionary for each schema by
        traversing the `dbtypes` dictionary.  Fills in the `tables`,
        `sequences`, `views` dictionaries for each schema by
        traversing the `dbtables` dictionary. Fills in the `functions`
        dictionary by traversing the `dbfunctions` dictionary.
        """
        for (sch, typ) in list(dbtypes.keys()):
            dbtype = dbtypes[(sch, typ)]
            assert self[sch]
            schema = self[sch]
            if isinstance(dbtype, Domain):
                if not hasattr(schema, 'domains'):
                    schema.domains = {}
                schema.domains.update({typ: dbtypes[(sch, typ)]})
            elif isinstance(dbtype, Enum) or isinstance(dbtype, Composite) \
                    or isinstance(dbtype, BaseType):
                if not hasattr(schema, 'types'):
                    schema.types = {}
                schema.types.update({typ: dbtypes[(sch, typ)]})
        for (sch, tbl) in list(dbtables.keys()):
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
        for (sch, fnc, arg) in list(dbfunctions.keys()):
            func = dbfunctions[(sch, fnc, arg)]
            assert self[sch]
            schema = self[sch]
            if not hasattr(schema, 'functions'):
                schema.functions = {}
            schema.functions.update({(fnc, arg): func})
            if hasattr(func, 'returns'):
                rettype = func.returns
                if rettype.upper().startswith("SETOF "):
                    rettype = rettype[6:]
                (retsch, rettyp) = split_schema_obj(rettype, sch)
                if (retsch, rettyp) in list(dbtables.keys()):
                    deptbl = dbtables[(retsch, rettyp)]
                    if not hasattr(func, 'dependent_table'):
                        func.dependent_table = deptbl
                    if not hasattr(deptbl, 'dependent_funcs'):
                        deptbl.dependent_funcs = []
                    deptbl.dependent_funcs.append(func)
        for (sch, opr, lft, rgt) in list(dbopers.keys()):
            oper = dbopers[(sch, opr, lft, rgt)]
            assert self[sch]
            schema = self[sch]
            if not hasattr(schema, 'operators'):
                schema.operators = {}
            schema.operators.update({(opr, lft, rgt): oper})
        for (sch, opc, idx) in list(dbopcls.keys()):
            opcl = dbopcls[(sch, opc, idx)]
            assert self[sch]
            schema = self[sch]
            if not hasattr(schema, 'operclasses'):
                schema.operclasses = {}
            schema.operclasses.update({(opc, idx): opcl})
        for (sch, opf, idx) in list(dbopfams.keys()):
            opfam = dbopfams[(sch, opf, idx)]
            assert self[sch]
            schema = self[sch]
            if not hasattr(schema, 'operfams'):
                schema.operfams = {}
            schema.operfams.update({(opf, idx): opfam})
        for (sch, cnv) in list(dbconvs.keys()):
            conv = dbconvs[(sch, cnv)]
            assert self[sch]
            schema = self[sch]
            if not hasattr(schema, 'conversions'):
                schema.conversions = {}
            schema.conversions.update({cnv: conv})
        for (sch, tsc) in list(dbtsconfigs.keys()):
            tscfg = dbtsconfigs[(sch, tsc)]
            assert self[sch]
            schema = self[sch]
            if not hasattr(schema, 'tsconfigs'):
                schema.tsconfigs = {}
            schema.tsconfigs.update({tsc: tscfg})
        for (sch, tsd) in list(dbtsdicts.keys()):
            tsdict = dbtsdicts[(sch, tsd)]
            assert self[sch]
            schema = self[sch]
            if not hasattr(schema, 'tsdicts'):
                schema.tsdicts = {}
            schema.tsdicts.update({tsd: tsdict})
        for (sch, tsp) in list(dbtspars.keys()):
            tspar = dbtspars[(sch, tsp)]
            assert self[sch]
            schema = self[sch]
            if not hasattr(schema, 'tsparsers'):
                schema.tsparsers = {}
            schema.tsparsers.update({tsp: tspar})
        for (sch, tst) in list(dbtstmpls.keys()):
            tstmpl = dbtstmpls[(sch, tst)]
            assert self[sch]
            schema = self[sch]
            if not hasattr(schema, 'tstempls'):
                schema.tstempls = {}
            schema.tstempls.update({tst: tstmpl})
        for (sch, ftb) in list(dbftables.keys()):
            ftbl = dbftables[(sch, ftb)]
            assert self[sch]
            schema = self[sch]
            if not hasattr(schema, 'ftables'):
                schema.ftables = {}
            schema.ftables.update({ftb: ftbl})
        for (sch, cll) in list(dbcolls.keys()):
            coll = dbcolls[(sch, cll)]
            assert self[sch]
            schema = self[sch]
            if not hasattr(schema, 'collations'):
                schema.collations = {}
            schema.collations.update({cll: coll})

    def to_map(self, no_owner=False, no_privs=False):
        """Convert the schema dictionary to a regular dictionary

        :param no_owner: exclude object owner information
        :param no_privs: exclude privilege information
        :return: dictionary

        Invokes the `to_map` method of each schema to construct a
        dictionary of schemas.
        """
        schemas = {}
        for sch in list(self.keys()):
            schemas.update(self[sch].to_map(self, no_owner, no_privs))
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
        for sch in list(inschemas.keys()):
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
                    except KeyError as exc:
                        exc.args = ("Previous name '%s' for schema '%s' "
                                   "not found" % (oldname, insch.name), )
                        raise
                else:
                    # create new schema
                    stmts.append(insch.create())
        # check database schemas
        for sch in list(self.keys()):
            # if missing and not 'public', drop it
            if sch not in ['public', 'pg_catalog'] and sch not in inschemas:
                self[sch].dropped = True
        return stmts

    def _drop(self):
        """Actually drop the schemas

        :return: SQL statements
        """
        stmts = []
        for sch in list(self.keys()):
            if sch != 'public' and hasattr(self[sch], 'dropped'):
                stmts.append(self[sch].drop())
        return stmts
