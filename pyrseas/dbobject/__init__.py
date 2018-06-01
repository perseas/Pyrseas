# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject
    ~~~~~~~~~~~~~~~~

    This defines two low level classes and an intermediate class.
    Most Pyrseas classes are derived from either DbObject or
    DbObjectDict.
"""
import os
import re
import string
from functools import wraps

from pyrseas.lib.pycompat import PY2, strtypes
from pyrseas.yamlutil import yamldump
from .privileges import privileges_to_map, add_grant, diff_privs
from .privileges import privileges_from_map


VALID_FIRST_CHARS = string.ascii_lowercase + '_'
VALID_CHARS = string.ascii_lowercase + string.digits + '_$'
RESERVED_WORDS = []
NON_FILENAME_CHARS = re.compile(r'\W', re.U)
MAX_PG_IDENT_LEN = 63
MAX_IDENT_LEN = int(os.environ.get("PYRSEAS_MAX_IDENT_LEN", 32))


def fetch_reserved_words(db):
    """Fetch PostgreSQL reserved words

    :param db: DbConnection object
    """
    global RESERVED_WORDS

    if len(RESERVED_WORDS) == 0:
        RESERVED_WORDS = [word[0] for word in
                          db.fetchall("""SELECT word FROM pg_get_keywords()
                                         WHERE catcode = 'R'""")]


def quote_id(name):
    """Quotes an identifier if necessary.

    :param name: string to be quoted

    :return: possibly quoted string
    """
    regular_id = True
    if not name[0] in VALID_FIRST_CHARS or name in RESERVED_WORDS:
        regular_id = False
    else:
        for ltr in name[1:]:
            if ltr not in VALID_CHARS:
                regular_id = False
                break

    return regular_id and name or '"%s"' % name


def split_schema_obj(obj, sch=None):
    """Return a (schema, object) tuple given a possibly schema-qualified name

    :param obj: object name or schema.object
    :param sch: schema name (defaults to 'pg_catalog')
    :return: tuple
    """
    def undelim(ident):
        if ident[0] == '"' and ident[-1] == '"':
            ident = ident[1:-1]
        return ident

    qualsch = sch
    if sch is None:
        qualsch = 'pg_catalog'
    if obj[0] == '"' and obj[-1] == '"':
        if '"."' in obj:
            (qualsch, obj) = obj.split('"."')
            qualsch = qualsch[1:]
            obj = obj[:-1]
        else:
            obj = obj[1:-1]
    else:
        # TODO: properly handle functions
        if '.' in obj and '(' not in obj:
            (qualsch, obj) = obj.split('.')
    if sch != qualsch:
        sch = qualsch
    return (undelim(sch), undelim(obj))


def split_func_args(obj):
    """Split function name and argument from a signature, e.g. fun(int, text)

    :param obj: The string to parse
    :return: 2-item tuple (name, args), args is a list of strings.

    TODO: make it safer against pathologic input (names containing' '( and ',')
    """
    tokens = obj.split('(')
    if len(tokens) != 2 or not tokens[1].endswith(')'):
        raise ValueError("not a valid function signature: '%s'" % obj)
    name = tokens[0]
    args = [arg.strip() for arg in tokens[1][:-1].split(',')]
    return name, args


def commentable(func):
    """Decorator to add comments to various objects"""
    @wraps(func)
    def add_comment(obj, *args, **kwargs):
        stmts = func(obj, *args, **kwargs)
        if obj.description is not None:
            stmts.append(obj.comment())
        return stmts
    return add_comment


def grantable(func):
    """Decorator to add GRANT to various objects"""
    @wraps(func)
    def grant(obj, *args, **kwargs):
        stmts = func(obj, *args, **kwargs)
        if hasattr(obj, 'privileges'):
            for priv in obj.privileges:
                stmts.append(add_grant(obj, priv))
        return stmts
    return grant


def ownable(func):
    """Decorator to add ALTER OWNER to various objects"""
    @wraps(func)
    def add_alter(obj, *args, **kwargs):
        stmts = func(obj, *args, **kwargs)
        if hasattr(obj, 'owner'):
            stmts.append(obj.alter_owner())
        return stmts
    return add_alter


class DbObject(object):
    "A single object in a database catalog, e.g., a schema, a table, a column"

    keylist = ['name']
    """List of attributes that uniquely identify the object in the catalogs

    See description of :meth:`key` for further details.
    """

    @property
    def objtype(self):
        """Type of object as an uppercase string, for SQL syntax generation

        This is used in most CREATE, ALTER and DROP statements.  It is
        also used by :meth:`extern_key` in lowercase form.
        """
        if self._objtype is None:
            self._objtype = self.__class__.__name__.upper()
        return self._objtype

    catalog = None
    """The name of the system catalog where these objects live
    """

    allprivs = ''

    def __init__(self, name, description=None, **attrs):
        """Initialize the catalog object from a dictionary of attributes

        :param name: name of object
        :param description: comment text describing object
        :param attrs: the dictionary of attributes

        Non-key attributes without a value are discarded. Values that
        are multi-line strings are treated specially so that YAML will
        output them in block style.
        """
        self.name = name
        self.description = description
        self.depends_on = []
        self.owner = None
        self.privileges = []
        self._objtype = None

    def _init_own_privs(self, owner=None, privileges=[]):
        """Initialize owner and privileges attributes

        :param owner: name of user that owns the object
-       :param privileges: privileges on object

        The vast majority of Postgres database objects have owner and
        privileges attributes.  Hence all base DbObject instances have
        those attributes.  This method allows separate initialization.
        """
        self.owner = owner
        if isinstance(privileges, strtypes):
            privileges = privileges.split(',')
        self.privileges = privileges or []

    def __repr__(self):
        return "<%s at 0x%x>" % (self.extern_key(), id(self))

    # hash and eq allow to use the objects as dict keys
    def __hash__(self):
        return hash((self.__class__, self.key()))

    def __eq__(self, other):
        if self.__class__ is other.__class__:
            return self.key() == other.key()
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    @staticmethod
    def query(dbversion=None):
        """The SQL SELECT query to fetch object instances from the catalogs

        :param dbversion: Postgres version identifier

        This is used by the method :meth:`fetch`.  The `dbversion`
        parameter is used in descendant classes to customize the
        queries according to the target Postgres version.
        """
        return ""

    def extern_key(self):
        """Return the key to be used in external maps for this object

        :return: string

        This is used for the first two levels of external maps.  The
        first level is the one that includes schemas, as well as
        extensions, languages, casts and foreign data wrappers.  The
        second level includes all schema-owned objects, i.e., tables,
        functions, operators, etc.  All subsequent levels, e.g.,
        primary keys, indexes, etc., currently use the object name as
        the external identifier, appearing in the map after an object
        grouping header, such as ``primary_key``.

        The common format for an external key is `object-type
        non-schema-qualified-name`, where `object-type` is the
        lowercase version of :attr:`objtype`, e.g., ``table
        tablename``.  Some object types require more, e.g., functions
        need the signature, so they override this implementation.

        """
        return '%s %s' % (self.objtype.lower(), self.name)

    def extern_filename(self, ext='yaml', truncate=False):
        """Return a filename to be used to output external files

        :param ext: file extension
        :param truncate: truncate filename to MAX_IDENT_LEN
        :return: filename string

        This is used for the first two levels of external (metadata)
        files.  The first level is the one that includes schemas, as
        well as extensions, languages, casts and FDWs.  The second
        level includes all schema-owned objects, i.e., tables,
        functions, operators, etc.

        The common format for the filename is `objtype.objname.yaml`,
        e.g., for a table `t1` the filename is "table.t1.yaml".  For
        an object name that has characters not allowed in filesystems,
        the characters are replaced by underscores.

        """
        max_len = MAX_IDENT_LEN if truncate else MAX_PG_IDENT_LEN

        def xfrm_filename(objtype, objid=None):
            """Generic transformation of object identifier to a filename

            :param objtype: object type
            :param objid: object identifier, usually the 'name' attribute
            :return: filename string
            """
            if objid:
                if PY2:
                    objid = objid.decode('utf_8')
                filename = '%s.%.*s.%s' % (
                    objtype, max_len, re.sub(NON_FILENAME_CHARS, '_', objid),
                    ext)
                if PY2:
                    filename = filename.encode('utf_8')
            else:
                filename = '%s.%s' % (objtype.replace(' ', '_'), ext)
            return filename.lower()

        if hasattr(self, 'single_extern_file') and self.single_extern_file:
            return xfrm_filename(self.objtype)

        return xfrm_filename(self.objtype, self.name)

    def key(self):
        """Return a tuple that identifies the database object

        :return: a single string or a tuple of strings

        This is used as key for all internal maps. The first-level
        objects (schemas, languages and casts) use the object name as
        the key. Second-level (schema-owned) objects usually use the
        schema name and the object name as the key. Some object types
        need longer keys, e.g., operators need schema name, operator
        symbols, left argument and right argument.

        Each class implementing an object type specifies a
        :attr:`keylist` attribute, i.e., a list giving the names of
        attributes making up the key.
        """
        lst = [getattr(self, k) for k in self.keylist]
        return len(lst) == 1 and lst[0] or tuple(lst)

    def identifier(self):
        """Returns a full identifier for the database object

        :return: string

        This is used by :meth:`comment`, :meth:`alter_owner` and
        :meth:`drop` to generate SQL syntax referring to the object.
        It does not include the object type, but it may include (in
        overriden methods) other elements, e.g., the arguments to a
        function.
        """
        return quote_id(self.__dict__[self.keylist[0]])

    def to_map(self, db, no_owner=False, no_privs=False, deepcopy=True):
        """Convert an object to a YAML-suitable format

        :param db: db used to tie the objects together
        :param no_owner: exclude object owner information
        :param no_privs: exclude privilege information
        :return: dictionary

        The return value, a Python dictionary, is equivalent to a YAML
        or JSON object.
        """
        import copy
        if deepcopy:
            dct = copy.deepcopy(self.__dict__)
        else:
            dct = self.__dict__.copy()
        for key in self.keylist:
            del dct[key]
        if self.description is None:
            del dct['description']
        if no_owner or self.owner is None:
            del dct['owner']
        if len(self.privileges) == 0 or no_privs:
            del dct['privileges']
        else:
            dct['privileges'] = self.map_privs()

        # Never dump the oid
        dct.pop('oid', None)

        # Only dump dependencies that can't be inferred from the context
        deps = set(dct.pop('depends_on', ()))
        deps -= self.get_implied_deps(db)
        if deps:
            dct['depends_on'] = sorted([dep.extern_key() for dep in deps])

        # Drop any private attributes
        for k in list(dct.keys()):
            if k.startswith('_'):
                del dct[k]

        return dct

    def map_privs(self):
        """Return a list of access privileges on the current object

        :return: list
        """
        privlist = []
        for prv in self.privileges:
            if prv:
                privlist.append(privileges_to_map(prv, self.allprivs,
                                                  self.owner))
        sorted_privlist = []
        for sortedItem in sorted([list(i.keys())[0] for i in privlist]):
            sorted_privlist.append([item for item in privlist
                                    if list(item.keys())[0] == sortedItem][0])
        return sorted_privlist

    def set_oldname(self, inobj):
        """Set oldname attribute if present in the input YAML map

        :param inobj: YAML map of input object
        """
        if 'oldname' in inobj:
            self.oldname = inobj.get('oldname')

    def fix_privileges(self):
        """Adjust raw privilege information from YAML map"""
        if len(self.privileges) > 0:
            if self.owner is None:
                raise ValueError(
                    "%s '%s' has privileges but no owner information" % (
                        self.objtype.capitalize(), self.name))
            else:
                self.privileges = privileges_from_map(
                    self.privileges, self.allprivs, self.owner)

    def _comment_text(self):
        """Return the text for the SQL COMMENT statement

        :return: string
        """
        if self.description is not None:
            return "'%s'" % self.description.replace("'", "''")
        else:
            return 'NULL'

    def comment(self):
        """Return SQL statement to create a COMMENT on the object

        :return: SQL statement
        """
        return "COMMENT ON %s %s IS %s" % (
            self.objtype, self.identifier(), self._comment_text())

    def alter_owner(self, owner=None):
        """Return ALTER statement to set the OWNER of an object

        :return: SQL statement
        """
        if self.owner != owner:
            return "ALTER %s %s OWNER TO %s" % (
                self.objtype, self.identifier(), owner or self.owner)
        else:
            return []

    def rename(self, oldname):
        """Return SQL statement to RENAME the object

        :param oldname: the old name for the object
        :return: SQL statement
        """
        return "ALTER %s %s RENAME TO %s" % (
            self.objtype, quote_id(oldname), quote_id(self.name))

    def create(self, dbversion=None):
        raise NotImplementedError

    def create_sql(self, dbversion=None):
        if hasattr(self, 'oldname') and self.oldname is not None:
            return self.rename(self.oldname)
        else:
            return self.create(dbversion)

    def alter(self, inobj, no_owner=False):
        """Generate SQL to transform an existing database object

        :param inobj: a YAML map defining the new object
        :return: list of SQL statements

        Compares the current object to an input object and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []
        if not no_owner and self.owner is not None and inobj.owner is not None:
            if inobj.owner != self.owner:
                stmts.append(self.alter_owner(inobj.owner))
        stmts.append(self.diff_privileges(inobj))
        stmts.append(self.diff_description(inobj))
        return stmts

    def drop(self):
        """Generate SQL to drop the current object

        :return: list of SQL statements
        """
        return ["DROP %s %s" % (self.objtype, self.identifier())]

    def diff_privileges(self, inobj):
        """Generate SQL statements to grant or revoke privileges

        :param inobj: a YAML map defining the input object
        :return: list of SQL statements
        """
        return diff_privs(self, self.privileges, inobj, inobj.privileges)

    def diff_description(self, inobj):
        """Generate SQL statements to add or change COMMENTs

        :param inobj: a YAML map defining the input object
        :return: list of SQL statements
        """
        stmts = []
        if self.description is not None:
            if inobj.description is not None:
                if self.description != inobj.description:
                    self.description = inobj.description
                    stmts.append(self.comment())
            else:
                self.description = None
                stmts.append(self.comment())
        else:
            if inobj.description is not None:
                self.description = inobj.description
                stmts.append(self.comment())
        return stmts

    def get_deps(self, db):
        """Return all the objects the object depends on

        The base implementation returns the explicit dependencies. Subclasses
        may extend this to include implicit ones, which are implied e.g. by
        containment in the yaml (such as an object on the schema they are on, a
        constraint on the domain it is defined for.

        :return: set of `DbObject`
        """
        deps = set()

        # The explicit dependencies
        for dep in self.depends_on:
            if isinstance(dep, strtypes):
                dep = db._get_by_extkey(dep)
            deps.add(dep)

        for dep in self.get_implied_deps(db):
            deps.add(dep)

        return deps

    def get_implied_deps(self, db):
        """Return the dependencies the object can handle without being explicit

        :return: set of `DbObject`
        """
        return set()


class DbSchemaObject(DbObject):
    "A database object that is owned by a certain schema"

    def __init__(self, name, schema='public', description=None, **attrs):
        super(DbSchemaObject, self).__init__(name, description, **attrs)
        self.schema = schema

    def identifier(self):
        """Return a full identifier for a schema object

        :return: string
        """
        return "%s.%s" % (quote_id(self.schema), quote_id(self.name))

    def qualname(self, schema=None, objname=None):
        """Return the schema-qualified name of self or a related object

        :return: string
        """
        if self.schema == schema and self.name == objname:
            return self.identifier()
        if objname is None:
            objname = self.name
        return "%s.%s" % (quote_id(schema or self.schema), quote_id(objname))

    def unqualify(self, objname):
        """Adjust the object name if it is qualified

        :param objname: object name
        :return: unqualified object name
        """
        if '.' in objname:
            (sch, objname) = split_schema_obj(objname, self.schema)
            assert sch == self.schema
            return objname
        else:
            return objname

    def extern_filename(self, ext='yaml'):
        """Return a filename to be used to output external files

        :param ext: file extension
        :return: filename string
        """
        return super(DbSchemaObject, self).extern_filename(ext, True)

    def rename(self, oldname):
        """Return SQL statement to RENAME the schema object

        :param oldname: the old name for the schema object
        :return: SQL statement
        """
        return "ALTER %s %s.%s RENAME TO %s" % (
            self.objtype, quote_id(self.schema), quote_id(oldname),
            quote_id(self.name))

    def get_implied_deps(self, db):
        deps = super(DbSchemaObject, self).get_implied_deps(db)

        # The schema of the object (if any) is always a dependency
        if hasattr(self, 'schema'):
            s = db.schemas.get(self.schema)
            if s:
                deps.add(s)

        return deps


class DbObjectDict(dict):
    """A dictionary of database objects, all of the same type.

    However, note that "type" sometimes refers to a polymorphic class.
    For example, a :class:`ConstraintDict` holds objects of type
    :class:`Constraint`, but the actual objects may be of class
    :class:`CheckConstraint`, :class:`PrimaryKey`, etc.
    """

    cls = DbObject
    """The possibly-polymorphic class, derived from :class:`DbObject` that
    the objects belong to.
    """

    def __init__(self, dbconn=None):
        """Initialize the dictionary

        :param dbconn: a DbConnection object

        If dbconn is not None, the _from_catalog method is called to
        initialize the dictionary from the catalogs.
        """
        dict.__init__(self)
        self.by_oid = {}
        self.dbconn = dbconn
        if dbconn:
            self._from_catalog()

    def _from_catalog(self):
        """Initialize the dictionary by querying the catalogs

        This is may be overriden by derived classes as needed.
        """
        for obj in self.fetch():
            if hasattr(obj, 'options'):
                if type(obj.options) is list:
                    obj.options = sorted(obj.options)
            self[obj.key()] = obj
            if hasattr(obj, 'oid'):
                self.by_oid[obj.oid] = obj

    def to_map(self, db, opts):
        """Convert the object dictionary to a regular dictionary

        :param db: db used to tie the objects together
        :param opts: options to include/exclude information, etc.
        :return: dictionary

        Invokes the `to_map` method of each object to construct the
        dictionary.  If `opts` specifies a directory, the objects are
        written to files in that directory.
        """
        objdict = {}
        for objkey in sorted(self.keys()):
            obj = self[objkey]
            objmap = obj.to_map(db, opts.no_owner, opts.no_privs)
            if objmap is not None:
                extkey = obj.extern_key()
                outobj = {extkey: objmap}
                if opts.multiple_files:
                    filepath = obj.extern_filename()
                    with open(os.path.join(opts.metadata_dir, filepath),
                              'a') as f:
                        f.write(yamldump(outobj))
                    outobj = {extkey: filepath}
                objdict.update(outobj)
        return objdict

    def fetch(self):
        """Fetch all objects from the catalogs using the associated
        :meth:`query` methods.

        :return: list of self.cls (polymorphic) objects

        """
        self.query = self.cls.query(self.dbconn.version)
        data = self.dbconn.fetchall(self.query)
        self.dbconn.rollback()
        return [self.cls(**dict(row)) for row in data]
