# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.dbtype
    ~~~~~~~~~~~~~~~~~~~~~~~

    This module defines six classes: DbType derived from
    DbSchemaObject, BaseType, Composite, Domain and Enum derived from
    DbType, and TypeDict derived from DbObjectDict.
"""

from pyrseas.dbobject import DbObjectDict, DbSchemaObject
from pyrseas.dbobject import split_schema_obj, commentable, ownable
from pyrseas.dbobject.constraint import CheckConstraint


ALIGNMENT_TYPES = {'c': 'char', 's': 'int2', 'i': 'int4', 'd': 'double'}
STORAGE_TYPES = {'p': 'plain', 'e': 'external', 'm': 'main', 'x': 'extended'}
OPT_FUNCS = ('receive', 'send', 'typmod_in', 'typmod_out', 'analyze')


class DbType(DbSchemaObject):
    """A composite, domain or enum type"""

    keylist = ['schema', 'name']
    catalog = 'pg_type'

    @property
    def objtype(self):
        return "TYPE"

    def find_defining_funcs(self, dbfuncs):
        return []


class BaseType(DbType):
    """A composite type"""

    def to_map(self, db, no_owner):
        """Convert a type to a YAML-suitable format

        :param no_owner: exclude type owner information
        :return: dictionary
        """
        dct = self._base_map(db, no_owner)
        if self.internallength < 0:
            dct['internallength'] = 'variable'
        dct['alignment'] = ALIGNMENT_TYPES[self.alignment]
        dct['storage'] = STORAGE_TYPES[self.storage]
        if self.delimiter == ',':
            del dct['delimiter']
        return dct

    @commentable
    @ownable
    def create(self):
        """Return SQL statements to CREATE the base type

        :return: SQL statements
        """
        stmts = []
        opt_clauses = []
        if hasattr(self, 'send'):
            opt_clauses.append("SEND = %s" % self.send)
        if hasattr(self, 'receive'):
            opt_clauses.append("RECEIVE = %s" % self.receive)
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
                         opt_clauses and ',\n    ' or '',
                         ',\n    '.join(opt_clauses)))
        return stmts

    def get_implied_deps(self, db):
        deps = super(BaseType, self).get_implied_deps(db)
        for f in self.find_defining_funcs(db.functions):
            deps.add(f)

        return deps

    def find_defining_funcs(self, dbfuncs):
        rv = []
        for attr, arg in [
                ('input', 'cstring'), ('output', self.qualname()),
                ('receive', 'internal'), ('send', self.qualname())]:
            f = getattr(self, attr, None)
            if not f:
                continue
            fschema, fname = split_schema_obj(f)
            rv.append(dbfuncs[fschema, fname, arg])
        return rv

    def drop(self):
        """Generate SQL to drop the type

        :return: list of SQL statements

        The CASCADE thing is mandatory to drop the functions too. There is
        a cyclic dependency so the dependency graph cannot be used. The
        functions will not be explicitly dropped.
        """
        return ["DROP %s %s CASCADE" % (self.objtype, self.identifier())]


class Composite(DbType):
    """A composite type"""

    def to_map(self, db, no_owner):
        """Convert a type to a YAML-suitable format

        :param no_owner: exclude type owner information
        :return: dictionary
        """
        if not hasattr(self, 'attributes'):
            return
        attrs = []
        for attr in self.attributes:
            att = attr.to_map(db, False)
            if att:
                attrs.append(att)
        dct = {'attributes': attrs}
        if not no_owner and self.owner is not None:
            dct.update(owner=self.owner)
        if self.description is not None:
            dct.update(description=self.description)
        return dct

    @commentable
    @ownable
    def create(self):
        """Return SQL statements to CREATE the composite type

        :return: SQL statements
        """
        attrs = []
        for att in self.attributes:
            attrs.append("    " + att.add()[0])
        return ["CREATE TYPE %s AS (\n%s)" % (
                self.qualname(), ",\n".join(attrs))]

    def alter(self, intype):
        """Generate SQL to transform an existing composite type

        :param intype: the new composite type
        :return: list of SQL statements

        Compares the type to an input type and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []
        if not hasattr(intype, 'attributes'):
            raise KeyError("Composite '%s' has no attributes" % intype.name)
        attrnames = [attr.name for attr in self.attributes
                     if not hasattr(attr, 'dropped')]
        dbattrs = len(attrnames)

        base = "ALTER TYPE %s\n    " % (self.qualname())
        # check input attributes
        for (num, inattr) in enumerate(intype.attributes):
            if hasattr(inattr, 'oldname'):
                assert(self.attributes[num].name == inattr.oldname)
                stmts.append(self.attributes[num].rename(inattr.name))
            # check existing attributes
            if num < dbattrs and self.attributes[num].name == inattr.name:
                (stmt, descr) = self.attributes[num].alter(inattr)
                if stmt:
                    stmts.append(base + stmt)
                if descr:
                    stmts.append(descr)
            # add new attributes
            elif inattr.name not in attrnames:
                (stmt, descr) = inattr.add()
                stmts.append(base + "ADD ATTRIBUTE %s" % stmt)
                if descr:
                    stmts.append(descr)

        # Check the columns to drop
        inattrnames = set(attr.name for attr in intype.attributes)
        for attr in self.attributes:
            if attr.name not in inattrnames:
                stmts.append(attr.drop())

        stmts.append(super(Composite, self).alter(intype))

        return stmts

    def get_implied_deps(self, db):
        deps = super(Composite, self).get_implied_deps(db)
        for col in self.attributes:
            type = db.find_type(col.type)
            if type is not None:
                deps.add(type)

        return deps


class Enum(DbType):
    "An enumerated type definition"

    @commentable
    @ownable
    def create(self):
        """Return SQL statements to CREATE the enum

        :return: SQL statements
        """
        lbls = ["'%s'" % lbl for lbl in self.labels]
        return ["CREATE TYPE %s AS ENUM (%s)" % (
                self.qualname(), ",\n    ".join(lbls))]


class Domain(DbType):
    "A domain definition"

    @property
    def objtype(self):
        return "DOMAIN"

    def to_map(self, db, no_owner):
        """Convert a domain to a YAML-suitable format

        :param no_owner: exclude domain owner information
        :return: dictionary
        """
        dct = self._base_map(db, no_owner)
        if hasattr(self, 'check_constraints'):
            if 'check_constraints' not in dct:
                dct.update(check_constraints={})
            for cns in list(self.check_constraints.values()):
                dct['check_constraints'].update(
                    self.check_constraints[cns.name].to_map(db, None))

        return dct

    @commentable
    @ownable
    def create(self):
        """Return SQL statements to CREATE the domain

        :return: SQL statements
        """
        create = "CREATE DOMAIN %s AS %s" % (self.qualname(), self.type)
        if hasattr(self, 'not_null'):
            create += ' NOT NULL'
        if hasattr(self, 'default'):
            create += ' DEFAULT ' + str(self.default)
        return [create]

    def get_implied_deps(self, db):
        deps = super(Domain, self).get_implied_deps(db)

        # depend on the base type
        # don't give errors in case it's a builtin
        tschema, tname = split_schema_obj(self.type)
        type = db.types.get((tschema, tname))
        if type:
            deps.add(type)

            # In my testing database there is a dependency on the output
            # function of the base type. TODO: investigate more.
            if hasattr(type, 'output'):
                fschema, fname = split_schema_obj(type.output)
                func = db.functions[fschema, fname, type.qualname()]
                deps.add(func)

        return deps


QUERY_PRE92 = \
    """SELECT t.oid, nspname AS schema, typname AS name, typtype AS kind,
              format_type(typbasetype, typtypmod) AS type,
              typnotnull AS not_null, typdefault AS default,
              ARRAY(SELECT enumlabel FROM pg_enum e WHERE t.oid = enumtypid
              ORDER BY e.oid) AS labels, rolname AS owner, NULL AS privileges,
              typinput::regproc AS input, typoutput::regproc AS output,
              typreceive::regproc AS receive, typsend::regproc AS send,
              typmodin::regproc AS typmod_in, typmodout::regproc AS typmod_out,
              typanalyze::regproc AS analyze, typlen AS internallength,
              typalign AS alignment, typstorage AS storage,
              typdelim AS delimiter, typcategory AS category,
              typispreferred AS preferred,
              obj_description(t.oid, 'pg_type') AS description
         FROM pg_type t JOIN pg_roles r ON (r.oid = typowner)
              JOIN pg_namespace n ON (typnamespace = n.oid)
              LEFT JOIN pg_class c ON (typrelid = c.oid)
        WHERE typisdefined AND (typtype in ('d', 'e')
              OR (typtype = 'c' AND relkind = 'c')
              OR (typtype = 'b' AND typarray != 0))
          AND nspname NOT IN ('pg_catalog', 'pg_toast', 'information_schema')
          AND t.oid NOT IN (SELECT objid FROM pg_depend WHERE deptype = 'e'
                            AND classid = 'pg_type'::regclass)
       ORDER BY nspname, typname"""


class TypeDict(DbObjectDict):
    "The collection of domains and enums in a database"

    cls = DbType
    query = \
        """SELECT t.oid,
                  nspname AS schema, typname AS name, typtype AS kind,
                  format_type(typbasetype, typtypmod) AS type,
                  typnotnull AS not_null, typdefault AS default,
                  ARRAY(SELECT enumlabel FROM pg_enum e WHERE t.oid = enumtypid
                  ORDER BY e.oid) AS labels, rolname AS owner,
                  array_to_string(typacl, ',') AS privileges,
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
                JOIN pg_roles r ON (r.oid = typowner)
                JOIN pg_namespace n ON (typnamespace = n.oid)
                LEFT JOIN pg_class c ON (typrelid = c.oid)
           WHERE typisdefined AND (typtype in ('d', 'e')
                 OR (typtype = 'c' AND relkind = 'c')
                 OR (typtype = 'b' AND typarray != 0))
             AND nspname NOT IN ('pg_catalog', 'pg_toast',
                                 'information_schema')
             AND t.oid NOT IN (
                 SELECT objid FROM pg_depend WHERE deptype = 'e'
                              AND classid = 'pg_type'::regclass)
           ORDER BY nspname, typname"""

    # TODO: consider to fetch all the objects belonging to extensions:
    # not to dump them but to trace dependency from objects to the extension

    def _from_catalog(self):
        """Initialize the dictionary of types by querying the catalogs"""
        if self.dbconn.version < 90200:
            self.query = QUERY_PRE92
        for dbtype in self.fetch():
            oid = dbtype.oid
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
                self.by_oid[oid] = self[sch, typ] = Domain(**dbtype.__dict__)
            elif kind == 'e':
                del dbtype.type
                self.by_oid[oid] = self[(sch, typ)] = Enum(**dbtype.__dict__)
                if not hasattr(self[sch, typ], 'labels'):
                    self[(sch, typ)].labels = {}
            elif kind == 'c':
                del dbtype.type
                self.by_oid[oid] = self[sch, typ] = Composite(
                    **dbtype.__dict__)
            elif kind == 'b':
                del dbtype.type
                for attr in OPT_FUNCS:
                    if getattr(dbtype, attr) == '-':
                        delattr(dbtype, attr)
                self.by_oid[oid] = self[sch, typ] = BaseType(**dbtype.__dict__)

    def from_map(self, schema, inobjs, newdb):
        """Initalize the dictionary of types by converting the input map

        :param schema: schema owning the types
        :param inobjs: YAML map defining the schema objects
        :param newdb: collection of dictionaries defining the database
        """
        for k in inobjs:
            (objtype, spc, key) = k.partition(' ')
            if spc != ' ' or objtype not in ['domain', 'type']:
                raise KeyError("Unrecognized object type: %s" % k)
            if objtype == 'domain':
                self[(schema.name, key)] = domain = Domain(
                    schema=schema.name, name=key)
                indomain = inobjs[k]
                if not indomain:
                    raise ValueError("Domain '%s' has no specification" % k)
                for attr, val in list(indomain.items()):
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
                for attr, val in list(intype.items()):
                    setattr(dtype, attr, val)
                if 'oldname' in intype:
                    dtype.oldname = intype['oldname']
                if 'description' in intype:
                    dtype.description = intype['description']
            else:
                raise KeyError("Unrecognized object type: %s" % k)

    def find(self, obj):
        """Find a type given its name.

        The name can contain modifiers such as arrays '[]' and attibutes '(3)'

        Return None if not found.
        """
        schema, name = split_schema_obj(obj)
        name = name.rstrip('[](,)0123456789')
        return self.get((schema, name))

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
        for (sch, typ) in dbcolumns:
            if (sch, typ) in self:
                assert isinstance(self[(sch, typ)], Composite)
                self[(sch, typ)].attributes = dbcolumns[(sch, typ)]
                for attr in dbcolumns[(sch, typ)]:
                    attr._type = self[(sch, typ)]
        for (sch, typ, cns) in dbconstrs:
            constr = dbconstrs[(sch, typ, cns)]
            if not hasattr(constr, 'target') or constr.target != 'd':
                continue
            assert self[(sch, typ)]
            constr._table = dbtype = self[(sch, typ)]
            if isinstance(constr, CheckConstraint):
                if not hasattr(dbtype, 'check_constraints'):
                    dbtype.check_constraints = {}
                dbtype.check_constraints.update({cns: constr})
