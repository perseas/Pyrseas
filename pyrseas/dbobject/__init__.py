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
from pyrseas.yamlutil import MultiLineStr, yamldump
from pyrseas.dbobject.privileges import privileges_to_map
from pyrseas.dbobject.privileges import add_grant, diff_privs


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
    :param sch: schema name (defaults to 'public')
    :return: tuple
    """
    qualsch = sch
    if sch is None:
        qualsch = 'public'
    if '.' in obj:
        (qualsch, obj) = obj.split('.')
    if obj[0] == '"' and obj[-1:] == '"':
        obj = obj[1:-1]
    if sch != qualsch:
        sch = qualsch
    return (sch, obj)


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
        for priv in obj.privileges:
            stmts.append(add_grant(obj, priv))
        return stmts
    return grant


def ownable(func):
    """Decorator to add ALTER OWNER to various objects"""
    @wraps(func)
    def add_alter(obj, *args, **kwargs):
        stmts = func(obj, *args, **kwargs)
        stmts.append(obj.alter_owner())
        return stmts
    return add_alter


class DbObject(object):
    "A single object in a database catalog, e.g., a schema, a table, a column"

    keylist = ['name']
    """List of attributes that uniquely identify the object in the catalogs

    See description of :meth:`key` for further details.
    """

    objtype = ''
    """Type of object as an uppercase string, for SQL syntax generation

    This is used in most CREATE, ALTER and DROP statements.  It is
    also used by :meth:`extern_key` in lowercase form.
    """

    allprivs = ''

    def __init__(self, name=None, description=None, owner=None,
                 privileges=None, **attrs):
        """Initialize the catalog object from a dictionary of attributes

        :param name: name of object
        :param description: comment text describing object
        :param owner: name of user that owns the object
        :param privileges: privileges on object
        :param attrs: dictionary of other attributes

        Non-key attributes without a value are discarded. Values that
        are multi-line strings are treated specially so that YAML will
        output them in block style.
        """
        self.name = name
        self.description = description
        self.owner = owner
        if isinstance(privileges, strtypes):
            privileges = privileges.split(',')
        self.privileges = privileges or []
        for key, val in list(attrs.items()):
            if val or key in self.keylist:
                if key in ['definition', 'description', 'source'] and \
                        isinstance(val, strtypes) and '\n' in val:
                    newval = []
                    for line in val.split('\n'):
                        if line and line[-1] in (' ', '\t'):
                            line = line.rstrip()
                        newval.append(line)
                    strval = '\n'.join(newval)
                    if PY2:
                        val = strval.encode('utf_8').decode('utf_8')
                    else:
                        val = MultiLineStr(strval)
                setattr(self, key, val)

    def extern_key(self):
        """Return the key to be used in external maps for this object

        :return: string

        This is used for the first two levels of external maps.  The
        first level is the one that includes schemas, as well as
        extensions, languages, casts and FDWs.  The second level
        includes all schema-owned objects, i.e., tables, functions,
        operators, etc.  All subsequent levels, e.g., primary keys,
        indexes, etc., currently use the object name as the external
        identifier, appearing in the map after an object grouping
        header, such as ``primary_key``.

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

        This is used for the first two levels of external maps.  The
        first level is the one that includes schemas, as well as
        extensions, languages, casts and FDWs.  The second level
        includes all schema-owned objects, i.e., tables, functions,
        operators, etc.

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

    def _base_map(self, no_owner=False, no_privs=False):
        """Return a base map, i.e., copy of attributes excluding keys

        :param no_owner: exclude object owner information
        :param no_privs: exclude privilege information
        :return: dictionary
        """
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
        return dct

    def to_map(self, no_owner=False, no_privs=False):
        """Convert an object to a YAML-suitable format

        :param no_owner: exclude object owner information
        :param no_privs: exclude privilege information
        :return: dictionary

        This base implementation simply copies the internal Python
        dictionary, removes the :attr:`keylist` attributes, and
        returns a new dictionary using the :meth:`extern_key` result
        as the key.
        """
        return self._base_map(no_owner, no_privs)

    def map_privs(self):
        """Return a list of access privileges on the current object

        :return: list
        """
        privlist = []
        for prv in self.privileges:
            if prv:
                privlist.append(privileges_to_map(prv, self.allprivs,
                                                  self.owner))
        return privlist

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

    def drop(self):
        """Return SQL statement to DROP the object

        :return: SQL statement
        """
        return "DROP %s %s" % (self.objtype, self.identifier())

    def rename(self, newname):
        """Return SQL statement to RENAME the object

        :param newname: the new name for the object
        :return: SQL statement
        """
        return "ALTER %s %s RENAME TO %s" % (self.objtype, self.name, newname)

    def diff_map(self, inobj, no_owner=False):
        """Generate SQL to transform an existing object

        :param inobj: a YAML map defining the new object
        :param no_owner: exclude object owner information
        :return: list of SQL statements

        Compares the object to an input object and generates SQL
        statements to transform it into the one represented by the
        input.  This base implementation simply deals with owners and
        comments.
        """
        stmts = []
        if not no_owner and self.owner is not None and inobj.owner is not None:
            if inobj.owner != self.owner:
                stmts.append(self.alter_owner(inobj.owner))
        stmts.append(self.diff_privileges(inobj))
        stmts.append(self.diff_description(inobj))
        return stmts

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


class DbSchemaObject(DbObject):
    "A database object that is owned by a certain schema"

    def __init__(self, schema, name, description=None, owner=None,
                 privileges=None, **attrs):
        """Initialize the catalog object from a dictionary of attributes

        :param schema: name of the schema owning the object
        :param name: name of object
        :param description: comment text describing object
        :param owner: name of user that owns the object
        :param privileges: privileges on object
        :param attrs: dictionary of other attributes
        """
        self.schema = schema
        super(DbSchemaObject, self).__init__(name, description, owner,
                                             privileges, **attrs)

    def identifier(self):
        """Return a full identifier for a schema object

        :return: string
        """
        return self.qualname()

    def qualname(self, objname=None):
        """Return the schema-qualified name of self or a related object

        :return: string

        No qualification is used if the schema is 'public'.
        """
        if objname is None:
            objname = self.name
        return self.schema == 'public' and quote_id(objname) \
            or "%s.%s" % (quote_id(self.schema), quote_id(objname))

    def unqualify(self):
        """Adjust the schema and table name if the latter is qualified"""
        if hasattr(self, 'table') and '.' in self.table:
            (sch, self.table) = split_schema_obj(self.table, self.schema)

    def extern_filename(self, ext='yaml'):
        """Return a filename to be used to output external files

        :param ext: file extension
        :return: filename string
        """
        return super(DbSchemaObject, self).extern_filename(ext, True)

    def drop(self):
        """Return a SQL DROP statement for the schema object

        :return: SQL statement
        """
        if not hasattr(self, 'dropped') or not self.dropped:
            self.dropped = True
            return "DROP %s %s" % (self.objtype, self.identifier())
        return []

    def rename(self, newname):
        """Return a SQL ALTER statement to RENAME the schema object

        :param newname: the new name of the object
        :return: SQL statement
        """
        return "ALTER %s %s RENAME TO %s" % (self.objtype, self.qualname(),
                                             newname)


class DbObjectDict(dict):
    """A dictionary of database objects, all of the same type"""

    cls = DbObject
    """The class, derived from :class:`DbObject` that the objects belong to.
    """
    query = ''
    """The SQL SELECT query to fetch object instances from the catalogs

    This is used by the method :meth:`fetch`.
    """

    def __init__(self, dbconn=None):
        """Initialize the dictionary

        :param dbconn: a DbConnection object

        If dbconn is not None, the _from_catalog method is called to
        initialize the dictionary from the catalogs.
        """
        dict.__init__(self)
        self.dbconn = dbconn
        if dbconn:
            self._from_catalog()

    def _from_catalog(self):
        """Initialize the dictionary by querying the catalogs

        This is may be overriden by derived classes as needed.
        """
        for obj in self.fetch():
            self[obj.key()] = obj

    def to_map(self,  opts):
        """Convert the object dictionary to a regular dictionary

        :param opts: options to include/exclude information, etc.
        :return: dictionary

        Invokes the `to_map` method of each object to construct the
        dictionary.  If opts specifies a directory, the objects are
        written to files in that directory.
        """
        objdict = {}
        for objkey in sorted(self.keys()):
            obj = self[objkey]
            objmap = obj.to_map(opts.no_owner, opts.no_privs)
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
        """Fetch all objects from the catalogs using the class :attr:`query`

        :return: list of self.cls objects
        """
        data = self.dbconn.fetchall(self.query)
        self.dbconn.rollback()
        return [self.cls(**dict(row)) for row in data]
