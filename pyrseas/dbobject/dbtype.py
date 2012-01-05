# -*- coding: utf-8 -*-
"""
    pyrseas.table
    ~~~~~~~~~~~~~

    This module defines six classes: DbType derived from
    DbSchemaObject, BaseType, Composite, Domain and Enum derived from
    DbType, and DbTypeDict derived from DbObjectDict.
"""
from pyrseas.dbobject import DbObjectDict, DbSchemaObject
from pyrseas.dbobject.schema import split_schema_obj
from pyrseas.dbobject.constraint import CheckConstraint


ALIGNMENT_TYPES = {'c': 'char', 's': 'int2', 'i': 'int4', 'd': 'double'}
STORAGE_TYPES = {'p': 'plain', 'e': 'external', 'm': 'main', 'x': 'extended'}
OPT_FUNCS = ('receive', 'send', 'typmod_in', 'typmod_out', 'analyze')


class DbType(DbSchemaObject):
    """A composite, domain or enum type"""

    keylist = ['schema', 'name']
    objtype = "TYPE"

    def diff_map(self, intype):
        """Generate SQL to transform an existing type

        :param intype: a YAML map defining the new type
        :return: list of SQL statements

        Compares the domain to an input type and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []
        stmts.append(self.diff_description(intype))
        return stmts


class BaseType(DbType):
    """A composite type"""

    def to_map(self):
        """Convert a type to a YAML-suitable format

        :return: dictionary
        """
        dct = self._base_map()
        del dct['dep_funcs']
        if self.internallength < 0:
            dct['internallength'] = 'variable'
        dct['alignment'] = ALIGNMENT_TYPES[self.alignment]
        dct['storage'] = STORAGE_TYPES[self.storage]
        if self.delimiter == ',':
            del dct['delimiter']
        return {self.extern_key(): dct}

    def create(self):
        """Return SQL statements to CREATE the base type

        :return: SQL statements
        """
        stmts = []
        stmts.append("CREATE TYPE %s" % self.qualname())
        stmts.append(self.dep_funcs['input'].create(basetype=True))
        stmts.append(self.dep_funcs['output'].create(basetype=True))
        opt_clauses = []
        for fnc in OPT_FUNCS:
            if fnc in self.dep_funcs:
                stmts.append(self.dep_funcs[fnc].create(basetype=True))
                opt_clauses.append("%s = %s" % (
                        fnc.upper(), self.dep_funcs[fnc].qualname()))
        if hasattr(self, 'internallength'):
            opt_clauses.append("INTERNALLENGTH = %s" % self.internallength)
        if hasattr(self, 'alignment'):
            opt_clauses.append("ALIGNMENT = %s" % self.alignment)
        if hasattr(self, 'storage'):
            opt_clauses.append("STORAGE = %s" % self.storage)
        if hasattr(self, 'delimiter'):
            opt_clauses.append("DELIMITER = '%s'" % self.delimiter)
        if hasattr(self, 'category'):
            opt_clauses.append("CATEGORY = '%s'" % self.category)
        if hasattr(self, 'preferred'):
            opt_clauses.append("PREFERRED = TRUE")
        stmts.append("CREATE TYPE %s (\n    INPUT = %s,"
                     "\n    OUTPUT = %s%s%s)" % (
                self.qualname(), self.input, self.output,
                opt_clauses and ',\n    ' or '', ',\n    '.join(opt_clauses)))
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts

    def drop(self):
        """Return SQL statement to DROP the base type

        :return: SQL statement

        We have to override the super method and add CASCADE to drop
        dependent functions.
        """
        return ["DROP TYPE %s CASCADE" % self.qualname()]


class Composite(DbType):
    """A composite type"""

    def to_map(self):
        """Convert a type to a YAML-suitable format

        :return: dictionary
        """
        if not hasattr(self, 'attributes'):
            return
        dct = {'attributes': [{att.name: att.type} for att in self.attributes]}
        if hasattr(self, 'description'):
            dct.update(description=self.description)
        return {self.extern_key(): dct}

    def create(self):
        """Return SQL statements to CREATE the composite type

        :return: SQL statements
        """
        stmts = []
        attrs = ["%s %s" % (att.name, att.type) for att in self.attributes]
        stmts.append("CREATE TYPE %s AS (%s)" % (
                self.qualname(), ",\n    ".join(attrs)))
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts


class Enum(DbType):
    "An enumerated type definition"

    def create(self):
        """Return SQL statements to CREATE the enum

        :return: SQL statements
        """
        stmts = []
        lbls = ["'%s'" % lbl for lbl in self.labels]
        stmts.append("CREATE TYPE %s AS ENUM (%s)" % (
                self.qualname(), ",\n    ".join(lbls)))
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts


class Domain(DbType):
    "A domain definition"

    objtype = "DOMAIN"

    def to_map(self):
        """Convert a domain to a YAML-suitable format

        :return: dictionary
        """
        dct = self._base_map()
        if hasattr(self, 'check_constraints'):
            if not 'check_constraints' in dct:
                dct.update(check_constraints={})
            for cns in self.check_constraints.values():
                dct['check_constraints'].update(
                    self.check_constraints[cns.name].to_map(None))

        return {self.extern_key(): dct}

    def create(self):
        """Return SQL statements to CREATE the domain

        :return: SQL statements
        """
        stmts = []
        create = "CREATE DOMAIN %s AS %s" % (self.qualname(), self.type)
        if hasattr(self, 'not_null'):
            create += ' NOT NULL'
        if hasattr(self, 'default'):
            create += ' DEFAULT ' + str(self.default)
        if hasattr(self, 'check_constraints'):
            cnslist = []
            for cns in self.check_constraints.values():
                cnslist.append(" CONSTRAINT %s CHECK (%s)" % (
                    cns.name, cns.expression))
            create += ", ".join(cnslist)
        stmts.append(create)
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts


class TypeDict(DbObjectDict):
    "The collection of domains and enums in a database"

    cls = DbType
    query = \
        """SELECT nspname AS schema, typname AS name, typtype AS kind,
                  format_type(typbasetype, typtypmod) AS type,
                  typnotnull AS not_null, typdefault AS default,
                  ARRAY(SELECT enumlabel FROM pg_enum e WHERE t.oid = enumtypid
                  ORDER BY e.oid) AS labels,
                  typinput::regproc AS input, typoutput::regproc AS output,
                  typreceive::regproc AS receive, typsend::regproc AS send,
                  typmodin::regproc AS typmod_in,
                  typmodout::regproc AS typmod_out,
                  typanalyze::regproc AS analyze,
                  typlen AS internallength, typalign AS alignment,
                  typstorage AS storage, typdelim AS delimiter,
                  typcategory AS category, typispreferred AS preferred,
                  obj_description(t.oid, 'pg_type') AS description
           FROM pg_type t
                JOIN pg_namespace n ON (typnamespace = n.oid)
                LEFT JOIN pg_class c ON (typrelid = c.oid)
           WHERE typisdefined AND (typtype in ('d', 'e')
                 OR (typtype = 'c' AND relkind = 'c')
                 OR (typtype = 'b' AND typarray != 0))
             AND nspname NOT IN ('pg_catalog', 'pg_toast',
                                 'information_schema')
           ORDER BY nspname, typname"""

    def _from_catalog(self):
        """Initialize the dictionary of types by querying the catalogs"""
        for dbtype in self.fetch():
            sch, typ = dbtype.key()
            kind = dbtype.kind
            del dbtype.kind
            if kind != 'b':
                del dbtype.input, dbtype.output
                del dbtype.receive, dbtype.send
                del dbtype.typmod_in, dbtype.typmod_out, dbtype.analyze
                del dbtype.internallength, dbtype.alignment, dbtype.storage
                del dbtype.delimiter, dbtype.category
            if kind == 'd':
                self[(sch, typ)] = Domain(**dbtype.__dict__)
            elif kind == 'e':
                del dbtype.type
                self[(sch, typ)] = Enum(**dbtype.__dict__)
            elif kind == 'c':
                del dbtype.type
                self[(sch, typ)] = Composite(**dbtype.__dict__)
            elif kind == 'b':
                del dbtype.type
                for attr in OPT_FUNCS:
                    if getattr(dbtype, attr) == '-':
                        delattr(dbtype, attr)
                self[(sch, typ)] = BaseType(**dbtype.__dict__)

    def from_map(self, schema, inobjs, newdb):
        """Initalize the dictionary of types by converting the input map

        :param schema: schema owning the types
        :param inobjs: YAML map defining the schema objects
        :param newdb: collection of dictionaries defining the database
        """
        for k in inobjs.keys():
            (objtype, spc, key) = k.partition(' ')
            if spc != ' ' or not objtype in ['domain', 'type']:
                raise KeyError("Unrecognized object type: %s" % k)
            if objtype == 'domain':
                self[(schema.name, key)] = domain = Domain(
                    schema=schema.name, name=key)
                indomain = inobjs[k]
                if not indomain:
                    raise ValueError("Domain '%s' has no specification" % k)
                for attr, val in indomain.items():
                    setattr(domain, attr, val)
                if 'oldname' in indomain:
                    domain.oldname = indomain['oldname']
                newdb.constraints.from_map(domain, indomain, 'd')
                if 'description' in indomain:
                    domain.description = indomain['description']
            elif objtype == 'type':
                intype = inobjs[k]
                if 'labels' in intype:
                    self[(schema.name, key)] = dtype = Enum(
                        schema=schema.name, name=key)
                    dtype.labels = intype['labels']
                elif 'attributes' in intype:
                    self[(schema.name, key)] = dtype = Composite(
                        schema=schema.name, name=key)
                    try:
                        newdb.columns.from_map(dtype, intype['attributes'])
                    except KeyError as exc:
                        exc.args = ("Type '%s' has no attributes" % key, )
                        raise
                elif 'input' in intype:
                    self[(schema.name, key)] = dtype = BaseType(
                        schema=schema.name, name=key)
                for attr, val in intype.items():
                    setattr(dtype, attr, val)
                if 'oldname' in intype:
                    dtype.oldname = intype['oldname']
                if 'description' in intype:
                    dtype.description = intype['description']
            else:
                raise KeyError("Unrecognized object type: %s" % k)

    def link_refs(self, dbcolumns, dbconstrs, dbfuncs):
        """Connect various objects to their corresponding types or domains

        :param dbcolumns: dictionary of columns
        :param dbconstrs: dictionary of constraints
        :param dbfuncs: dictionary of functions

        Fills the `check_constraints` dictionaries for each domain by
        traversing the `dbconstrs` dictionary. Fills the attributes
        list for composite types. Fills the dependent functions
        dictionary for base types.
        """
        for (sch, typ) in dbcolumns.keys():
            if (sch, typ) in self:
                assert isinstance(self[(sch, typ)], Composite)
                self[(sch, typ)].attributes = dbcolumns[(sch, typ)]
        for (sch, typ, cns) in dbconstrs.keys():
            constr = dbconstrs[(sch, typ, cns)]
            if not hasattr(constr, 'target') or constr.target != 'd':
                continue
            assert self[(sch, typ)]
            dbtype = self[(sch, typ)]
            if isinstance(constr, CheckConstraint):
                if not hasattr(dbtype, 'check_constraints'):
                    dbtype.check_constraints = {}
                dbtype.check_constraints.update({cns: constr})
        for (sch, typ) in self:
            dbtype = self[(sch, typ)]
            if isinstance(dbtype, BaseType):
                if not hasattr(dbtype, 'dep_funcs'):
                    dbtype.dep_funcs = {}
                (sch, infnc) = split_schema_obj(dbtype.input, sch)
                args = 'cstring'
                if not (sch, infnc, args) in dbfuncs:
                    args = 'cstring, oid, integer'
                func = dbfuncs[(sch, infnc, args)]
                dbtype.dep_funcs.update({'input': func})
                func._dep_type = dbtype
                (sch, outfnc) = split_schema_obj(dbtype.output, sch)
                func = dbfuncs[(sch, outfnc, dbtype.qualname())]
                dbtype.dep_funcs.update({'output': func})
                func._dep_type = dbtype
                for attr in OPT_FUNCS:
                    if hasattr(dbtype, attr):
                        (sch, fnc) = split_schema_obj(
                            getattr(dbtype, attr), sch)
                        if attr == 'receive':
                            arg = 'internal'
                        elif attr == 'send':
                            arg = dbtype.qualname()
                        elif attr == 'typmod_in':
                            arg = 'cstring[]'
                        elif attr == 'typmod_out':
                            arg = 'integer'
                        elif attr == 'analyze':
                            arg = 'internal'
                        func = dbfuncs[(sch, fnc, arg)]
                        dbtype.dep_funcs.update({attr: func})
                        func._dep_type = dbtype

    def diff_map(self, intypes):
        """Generate SQL to transform existing domains and types

        :param intypes: a YAML map defining the new domains/types
        :return: list of SQL statements

        Compares the existing domain/type definitions, as fetched from
        the catalogs, to the input map and generates SQL statements to
        transform the domains/types accordingly.
        """
        stmts = []
        # check input types
        for (sch, typ) in intypes.keys():
            intype = intypes[(sch, typ)]
            # does it exist in the database?
            if (sch, typ) not in self:
                if not hasattr(intype, 'oldname'):
                    # create new type
                    stmts.append(intype.create())
                else:
                    stmts.append(self[(sch, intype.oldname)].rename(typ))
                    del self[(sch, intype.oldname)]

        # check existing types
        for (sch, typ) in self.keys():
            dbtype = self[(sch, typ)]
            # if missing, mark it for dropping
            if (sch, typ) not in intypes:
                dbtype.dropped = False
            else:
                # check type objects
                stmts.append(dbtype.diff_map(intypes[(sch, typ)]))

        return stmts

    def _drop(self):
        """Actually drop the types

        :return: SQL statements
        """
        stmts = []
        for (sch, typ) in self.keys():
            dbtype = self[(sch, typ)]
            if hasattr(dbtype, 'dropped'):
                stmts.append(dbtype.drop())
                if isinstance(dbtype, BaseType):
                    for func in dbtype.dep_funcs.keys():
                        if func in ['typmod_in', 'typmod_out', 'analyze']:
                            stmts.append(dbtype.dep_funcs[func].drop())
        return stmts
