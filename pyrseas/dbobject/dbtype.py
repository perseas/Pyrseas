# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.dbtype
    ~~~~~~~~~~~~~~~~~~~~~~~

    This module defines seven classes: DbType derived from
    DbSchemaObject, BaseType, Composite, Domain, Enum and Range derived
    from DbType, and TypeDict derived from DbObjectDict.
"""

from . import DbObjectDict, DbSchemaObject
from . import split_schema_obj, commentable, ownable
from .constraint import CheckConstraint

ALIGNMENT_TYPES = {'c': 'char', 's': 'int2', 'i': 'int4', 'd': 'double'}
STORAGE_TYPES = {'p': 'plain', 'e': 'external', 'm': 'main', 'x': 'extended'}


class DbType(DbSchemaObject):
    """A user-defined type, such as a composite, domain or enum"""

    keylist = ['schema', 'name']
    catalog = 'pg_type'

    def __init__(self, name, schema, description, owner, privileges):
        """Initialize the type

        :param name: type name (from typname)
        :param schema: schema name (from typnamespace)
        :param description: comment text (from obj_description())
        :param owner: owner name (from rolname via typowner)
        :param privileges: access privileges (from typacl)
        """
        super(DbType, self).__init__(name, schema, description)
        self._init_own_privs(owner, privileges)

    @property
    def objtype(self):
        return "TYPE"

    def find_defining_funcs(self, dbfuncs):
        return []


class BaseType(DbType):
    """A base type"""

    def __init__(self, name, schema, description, owner, privileges,
                 input, output, receive=None, send=None, typmod_in=None,
                 typmod_out=None, analyze=None, internallength=1,
                 alignment=None, storage=None, delimiter=',',
                 category=None, preferred=False,
                 oid=None):
        """Initialize the base type

        :param name-privileges: see DbType.__init__ params
        :param input: input function (see typinput)
        :param output: output function (see typoutput)
        :param receive: input conversion function (see typreceive)
        :param send: output conversion function (see typsend)
        :param typmod_in: type modifier input function (see typmodin)
        :param typmod_out: type modifier output function (see typmodout)
        :param analyze: custom ANALYZE function (see typanalyze)
        :param internallength: length in bytes or -1 (variable) (see typlen)
        :param alignment: storage alignment (see typalign)
        :param storage: storage type for varlena types (see typstorage)
        :param delimiter: delimiter character for array type (see typdelim)
        :param category: PG data type classification (see typcategory)
        :param preferred: preferred cast target? (see typispreferred)
        """
        super(BaseType, self).__init__(name, schema, description, owner,
                                       privileges)
        self.input = self.unqualify(input)
        self.output = self.unqualify(output)
        self.receive = receive if receive != '-' else None
        self.send = send if send != '-' else None
        self.typmod_in = typmod_in if typmod_in != '-' else None
        self.typmod_out = typmod_out if typmod_out != '-' else None
        self.analyze = analyze if analyze != '-' else None
        self.internallength = internallength
        if alignment is not None and len(alignment) == 1:
            self.alignment = ALIGNMENT_TYPES[alignment]
        else:
            assert alignment in ALIGNMENT_TYPES.values()
            self.alignment = alignment
        if storage is not None and len(storage) == 1:
            self.storage = STORAGE_TYPES[storage]
        else:
            assert storage in STORAGE_TYPES.values()
            self.storage = storage
        self.delimiter = delimiter
        self.category = category
        self.preferred = preferred
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT nspname AS schema, typname AS name, rolname AS owner,
                   array_to_string(typacl, ',') AS privileges,
                   typinput::regproc AS input, typoutput::regproc AS output,
                   typreceive::regproc AS receive, typsend::regproc AS send,
                   typmodin::regproc AS typmod_in,
                   typmodout::regproc AS typmod_out,
                   typanalyze::regproc AS analyze,
                   typlen AS internallength, typalign AS alignment,
                   typstorage AS storage, typdelim AS delimiter,
                   typcategory AS category, typispreferred AS preferred,
                   obj_description(t.oid, 'pg_type') AS description, t.oid
            FROM pg_type t JOIN pg_roles r ON (r.oid = typowner)
                 JOIN pg_namespace n ON (typnamespace = n.oid)
                 LEFT JOIN pg_class c ON (typrelid = c.oid)
            WHERE typisdefined AND typtype = 'b' AND typarray != 0
              AND nspname NOT IN ('pg_catalog', 'pg_toast',
                                  'information_schema')
              AND t.oid NOT IN (
                  SELECT objid FROM pg_depend WHERE deptype = 'e'
                               AND classid = 'pg_type'::regclass)
            ORDER BY nspname, typname"""

    @staticmethod
    def from_map(name, schema, inobj):
        """Initialize a BaseType instance from a YAML map

        :param name: BaseType name
        :param schema: schema map
        :param inobj: YAML map of the BaseType
        :return: BaseType instance
        """
        obj = BaseType(
            name, schema.name, inobj.pop('description', None),
            inobj.pop('owner', None), inobj.pop('privileges', []),
            inobj.pop('input', None), inobj.pop('output', None),
            inobj.pop('receive', None), inobj.pop('send', None),
            inobj.pop('typmod_in', None), inobj.pop('typmod_out', None),
            inobj.pop('analyze', None), inobj.pop('internallength', 1),
            inobj.pop('alignment', None), inobj.pop('storage', None),
            inobj.pop('delimiter', ','), inobj.pop('category', None),
            inobj.pop('preferred', False))
        obj.fix_privileges()
        obj.set_oldname(inobj)
        return obj

    def to_map(self, db, no_owner, no_privs):
        """Convert a type to a YAML-suitable format

        :param no_owner: exclude type owner information
        :return: dictionary
        """
        dct = super(BaseType, self).to_map(db, no_owner, no_privs)
        for attr in ('receive', 'send', 'typmod_in', 'typmod_out', 'analyze',
                     'alignment', 'storage', 'category'):
            if getattr(self, attr) is None:
                dct.pop(attr)
        if self.internallength < 0:
            dct['internallength'] = 'variable'
        if self.delimiter == ',':
            dct.pop('delimiter')
        if self.preferred is False:
            dct.pop('preferred')
        return dct

    @commentable
    @ownable
    def create(self, dbversion=None):
        """Return SQL statements to CREATE the base type

        :return: SQL statements
        """
        stmts = []
        opt_clauses = []
        if self.send is not None:
            opt_clauses.append("SEND = %s" % self.send)
        if self.receive is not None:
            opt_clauses.append("RECEIVE = %s" % self.receive)
        opt_clauses.append("INTERNALLENGTH = %s" % self.internallength)
        if self.alignment is not None:
            opt_clauses.append("ALIGNMENT = %s" % self.alignment)
        if self.storage is not None:
            opt_clauses.append("STORAGE = %s" % self.storage)
        if self.delimiter is not None and self.delimiter != ',':
            opt_clauses.append("DELIMITER = '%s'" % self.delimiter)
        if self.category is not None:
            opt_clauses.append("CATEGORY = '%s'" % self.category)
        if self.preferred:
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
            fschema, fname = split_schema_obj(f, self.schema)
            rv.append(dbfuncs[fschema, fname, arg])
        return rv

    def drop(self):
        """Generate SQL to drop the type (and related functions)

        :return: list of SQL statements
        """
        # The CASCADE clause is required to also drop the related
        # functions.  There is a cyclic dependency so the dependency
        # graph cannot be used. The functions will not be explicitly
        # dropped.
        return ["DROP %s %s CASCADE" % (self.objtype, self.identifier())]


class Composite(DbType):
    """A composite type"""

    def __init__(self, name, schema, description, owner, privileges,
                 oid=None):
        """Initialize the composite type

        :param name-privileges: see DbType.__init__ params
        """
        super(Composite, self).__init__(name, schema, description, owner,
                                        privileges)
        self.attributes = []
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT nspname AS schema, typname AS name, rolname AS owner,
                   array_to_string(typacl, ',') AS privileges,
                   obj_description(t.oid, 'pg_type') AS description, t.oid
            FROM pg_type t JOIN pg_roles r ON (r.oid = typowner)
                 JOIN pg_namespace n ON (typnamespace = n.oid)
                 LEFT JOIN pg_class c ON (typrelid = c.oid)
            WHERE typisdefined AND (typtype = 'c' AND relkind = 'c')
              AND nspname NOT IN ('pg_catalog', 'pg_toast',
                                  'information_schema')
              AND t.oid NOT IN (
                  SELECT objid FROM pg_depend WHERE deptype = 'e'
                               AND classid = 'pg_type'::regclass)
            ORDER BY nspname, typname"""

    @staticmethod
    def from_map(name, schema, inobj):
        """Initialize a Composite instance from a YAML map

        :param name: Composite name
        :param schema: schema map
        :param inobj: YAML map of the Composite
        :return: Composite instance
        """
        obj = Composite(
            name, schema.name, inobj.pop('description', None),
            inobj.pop('owner', None), inobj.pop('privileges', []))
        obj.fix_privileges()
        obj.set_oldname(inobj)
        return obj

    def to_map(self, db, no_owner, no_privs):
        """Convert a type to a YAML-suitable format

        :param no_owner: exclude type owner information
        :return: dictionary
        """
        if len(self.attributes) == 0:
            return
        dct = super(Composite, self).to_map(db, no_owner, no_privs)
        attrs = []
        for attr in self.attributes:
            att = attr.to_map(db, False)
            if att:
                attrs.append(att)
        dct['attributes'] = attrs
        return dct

    @commentable
    @ownable
    def create(self, dbversion=None):
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
        if len(intype.attributes) == 0:
            raise KeyError("Composite '%s' has no attributes" % intype.name)
        attrnames = [attr.name for attr in self.attributes if not attr.dropped]
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

    def __init__(self, name, schema, description, owner, privileges,
                 labels, oid=None):
        """Initialize the enumerated type

        :param name-privileges: see DbType.__init__ params
        """
        super(Enum, self).__init__(name, schema, description, owner,
                                   privileges)
        self.labels = labels
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT nspname AS schema, typname AS name, rolname AS owner,
                   array_to_string(typacl, ',') AS privileges,
                   ARRAY(SELECT enumlabel FROM pg_enum e
                         WHERE t.oid = enumtypid
                         ORDER BY e.oid) AS labels,
                   obj_description(t.oid, 'pg_type') AS description, t.oid
            FROM pg_type t JOIN pg_roles r ON (r.oid = typowner)
                 JOIN pg_namespace n ON (typnamespace = n.oid)
                 LEFT JOIN pg_class c ON (typrelid = c.oid)
            WHERE typisdefined AND typtype = 'e'
              AND nspname NOT IN ('pg_catalog', 'pg_toast',
                                  'information_schema')
              AND t.oid NOT IN (
                  SELECT objid FROM pg_depend WHERE deptype = 'e'
                               AND classid = 'pg_type'::regclass)
            ORDER BY nspname, typname"""

    @staticmethod
    def from_map(name, schema, inobj):
        """Initialize an Enum instance from a YAML map

        :param name: Enum name
        :param schema: schema map
        :param inobj: YAML map of the Enum
        :return: Enum instance
        """
        obj = Enum(
            name, schema.name, inobj.pop('description', None),
            inobj.pop('owner', None), inobj.pop('privileges', []),
            inobj.pop('labels', []))
        obj.fix_privileges()
        obj.set_oldname(inobj)
        return obj

    @commentable
    @ownable
    def create(self, dbversion=None):
        """Return SQL statements to CREATE the enum

        :return: SQL statements
        """
        lbls = ["'%s'" % lbl for lbl in self.labels]
        return ["CREATE TYPE %s AS ENUM (%s)" % (
                self.qualname(), ",\n    ".join(lbls))]

    def alter(self, intype, no_owner=False):
        """Generate SQL to transform an existing enum type

        :param intype: the new enum type
        :return: list of SQL statements

        Compares the enum to an input enum and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []
        if self.labels != intype.labels:
            stmts.append(self.drop())
            stmts.append(intype.create())
        stmts.append(super(Enum, self).alter(intype, no_owner))
        return stmts


class Domain(DbType):
    "A domain definition"

    def __init__(self, name, schema, description, owner, privileges,
                 type, not_null=False, default=None,
                 oid=None):
        """Initialize the domain

        :param name-privileges: see DbType.__init__ params
        :param type: type modifier (see typtypmod)
        :param not_null: not null indicator (see typnotnull)
        :param default: default value (see typdefault)
        """
        super(Domain, self).__init__(name, schema, description, owner,
                                     privileges)
        self.type = type
        self.not_null = not_null
        self.default = default
        self.check_constraints = {}
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT nspname AS schema, typname AS name, rolname AS owner,
                   format_type(typbasetype, typtypmod) AS type,
                   typnotnull AS not_null, typdefault AS default,
                   array_to_string(typacl, ',') AS privileges,
                   obj_description(t.oid, 'pg_type') AS description, t.oid
            FROM pg_type t JOIN pg_roles r ON (r.oid = typowner)
                 JOIN pg_namespace n ON (typnamespace = n.oid)
                 LEFT JOIN pg_class c ON (typrelid = c.oid)
            WHERE typisdefined AND typtype = 'd'
              AND nspname NOT IN ('pg_catalog', 'pg_toast',
                                  'information_schema')
              AND t.oid NOT IN (
                  SELECT objid FROM pg_depend WHERE deptype = 'e'
                               AND classid = 'pg_type'::regclass)
            ORDER BY nspname, typname"""

    @staticmethod
    def from_map(name, schema, inobj):
        """Initialize an Domain instance from a YAML map

        :param name: Domain name
        :param schema: schema map
        :param inobj: YAML map of the Domain
        :return: Domain instance
        """
        obj = Domain(
            name, schema.name, inobj.pop('description', None),
            inobj.pop('owner', None), inobj.pop('privileges', []),
            inobj.pop('type', None), inobj.pop('not_null', False),
            inobj.pop('default', None))
        obj.fix_privileges()
        obj.set_oldname(inobj)
        return obj

    @property
    def objtype(self):
        return "DOMAIN"

    def to_map(self, db, no_owner, no_privs):
        """Convert a domain to a YAML-suitable format

        :param no_owner: exclude domain owner information
        :return: dictionary
        """
        dct = super(Domain, self).to_map(db, no_owner, no_privs)
        if self.not_null is False:
            dct.pop('not_null')
        if self.default is None:
            dct.pop('default')
        if len(self.check_constraints) > 0:
            for cns in list(self.check_constraints.values()):
                dct['check_constraints'].update(
                    self.check_constraints[cns.name].to_map(db, None))
        else:
            dct.pop('check_constraints')

        return dct

    @commentable
    @ownable
    def create(self, dbversion=None):
        """Return SQL statements to CREATE the domain

        :return: SQL statements
        """
        create = "CREATE DOMAIN %s AS %s" % (self.qualname(), self.type)
        if self.not_null:
            create += ' NOT NULL'
        if self.default is not None:
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


class Range(DbType):
    "A range type definition"

    def __init__(self, name, schema, description, owner, privileges,
                 subtype, canonical=None, subtype_diff=None,
                 oid=None):
        """Initialize the range type

        :param name-privileges: see DbType.__init__ params
        :param subtype: type of range elements (from rngsubtype)
        """
        super(Range, self).__init__(name, schema, description, owner,
                                    privileges)
        self.subtype = subtype
        self.canonical = canonical if canonical != '-' else None
        self.subtype_diff = subtype_diff if subtype_diff != '-' else None
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT nspname AS schema, t.typname AS name, rolname AS owner,
                   st.typname AS subtype, rn.rngcanonical AS canonical,
                   rn.rngsubdiff AS subtype_diff,
                   array_to_string(t.typacl, ',') AS privileges,
                   obj_description(t.oid, 'pg_type') AS description, t.oid
            FROM pg_type t JOIN pg_range rn ON rngtypid = t.oid
                 JOIN pg_type st ON rngsubtype = st.oid
                 JOIN pg_roles r ON (r.oid = t.typowner)
                 JOIN pg_namespace n ON (t.typnamespace = n.oid)
            WHERE t.typisdefined AND t.typtype = 'r'
              AND nspname NOT IN ('pg_catalog', 'pg_toast',
                                  'information_schema')
              AND t.oid NOT IN (
                  SELECT objid FROM pg_depend WHERE deptype = 'e'
                               AND classid = 'pg_type'::regclass)
            ORDER BY nspname, t.typname"""

    @staticmethod
    def from_map(name, schema, inobj):
        """Initialize a Range instance from a YAML map

        :param name: Range name
        :param schema: schema map
        :param inobj: YAML map of the Range
        :return: Range instance
        """
        obj = Range(
            name, schema.name, inobj.pop('description', None),
            inobj.pop('owner', None), inobj.pop('privileges', []),
            inobj.pop('subtype', None), inobj.pop('canonical', None),
            inobj.pop('subtype_diff', None))
        obj.fix_privileges()
        obj.set_oldname(inobj)
        return obj

    def to_map(self, db, no_owner, no_privs):
        """Convert a range type to a YAML-suitable format

        :param no_owner: exclude type owner information
        :return: dictionary
        """
        dct = super(Range, self).to_map(db, no_owner, no_privs)
        for attr in ('canonical', 'subtype_diff'):
            if getattr(self, attr) is None:
                dct.pop(attr)
        return dct

    @commentable
    @ownable
    def create(self, dbversion=None):
        """Return SQL statements to CREATE the range

        :return: SQL statements
        """
        clauses = []
        if self.canonical is not None:
            clauses.append("CANONICAL = %s" % self.canonical)
        if self.subtype_diff is not None:
            clauses.append("SUBTYPE_DIFF = %s" % self.subtype_diff)
        return ["CREATE TYPE %s AS RANGE (SUBTYPE = %s%s%s)" % (
            self.qualname(), self.subtype,
            clauses and ",\n    " or "", ",\n    ".join(clauses))]

    def alter(self, intype, no_owner=False):
        """Generate SQL to transform an existing range type

        :param intype: the new range type
        :return: list of SQL statements

        Compares the range to an input range and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []
        stmts.append(super(Range, self).alter(intype, no_owner))
        return stmts


class TypeDict(DbObjectDict):
    "The collection of user-defined types in a database"

    cls = DbType
    # TODO: consider to fetch all the objects belonging to extensions:
    # not to dump them but to trace dependency from objects to the extension

    def _from_catalog(self):
        """Initialize the dictionary of types by querying the catalogs"""
        for cls in (BaseType, Composite, Domain, Enum, Range):
            self.cls = cls
            for obj in self.fetch():
                self[obj.key()] = obj
                self.by_oid[obj.oid] = obj

    def from_map(self, schema, inobjs, newdb):
        """Initialize the dictionary of types by converting the input map

        :param schema: schema owning the types
        :param inobjs: YAML map defining the schema objects
        :param newdb: collection of dictionaries defining the database
        """
        for k in inobjs:
            (objtype, spc, key) = k.partition(' ')
            if spc != ' ' or objtype not in ['domain', 'type']:
                raise KeyError("Unrecognized object type: %s" % k)
            if objtype == 'domain':
                inobj = inobjs[k]
                self[(schema.name, key)] = obj = Domain.from_map(
                    key, schema, inobj)
                newdb.constraints.from_map(obj, inobj, 'd')
            elif objtype == 'type':
                inobj = inobjs[k]
                if 'input' in inobj:
                    self[(schema.name, key)] = BaseType.from_map(
                        key, schema, inobj)
                elif 'attributes' in inobj:
                    self[(schema.name, key)] = obj = Composite.from_map(
                        key, schema, inobj)
                    try:
                        newdb.columns.from_map(obj, inobj['attributes'])
                    except KeyError as exc:
                        exc.args = ("Type '%s' has no attributes" % key, )
                        raise
                elif 'labels' in inobj:
                    self[(schema.name, key)] = obj = Enum.from_map(
                        key, schema, inobj)
                elif 'subtype' in inobj:
                    self[(schema.name, key)] = obj = Range.from_map(
                        key, schema, inobj)
            else:
                raise KeyError("Unrecognized object type: %s" % k)

    def find(self, obj):
        """Find a type given its name.

        The name can contain modifiers such as arrays '[]' and attributes '(3)'

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
            if isinstance(constr, CheckConstraint) and \
               constr.is_domain_check:
                constr._table = dbtype = self[(sch, typ)]
                dbtype.check_constraints.update({cns: constr})
