# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.foreign
    ~~~~~~~~~~~~~~~~~~~~~~~~

    This defines nine classes: DbObjectWithOptions derived from
    DbObject, ForeignDataWrapper, ForeignServer and UserMapping
    derived from DbObjectWithOptions, ForeignDataWrapperDict,
    ForeignServerDict and UserMappingDict derived from DbObjectDict,
    ForeignTable derived from DbObjectWithOptions and Table, and
    ForeignTableDict derived from ClassDict.
"""
from . import DbObjectDict, DbObject
from . import quote_id, commentable, ownable, grantable
from .table import ClassDict, Table


class DbObjectWithOptions(DbObject):
    """Helper class for database objects with OPTIONS clauses"""

    def __init__(self, name, options):
        """Initialize the database object with options

        :param name: object name (from fdwname, srvname, etc.)
        :param options: object specific options (from fdwoptions, etc.)
        """
        super(DbObjectWithOptions, self).__init__(name, None)
        self.options = {} if options is None else options

    def to_map(self, db, no_owner=False, no_privs=False):
        """Convert objects to a YAML-suitable format

        :param no_owner: exclude object owner information
        :param no_privs: exclude privilege information
        :return: dictionary
        """
        dct = super(DbObjectWithOptions, self).to_map(db, no_owner, no_privs)
        if len(self.options) == 0:
            dct.pop('options')
        return dct

    def options_clause(self):
        """Create the OPTIONS clause

        :param optdict: the dictionary of options
        :return: SQL OPTIONS clause
        """
        opts = []
        for opt in self.options:
            (nm, val) = opt.split('=', 1)
            opts.append("%s '%s'" % (nm, val))
        return "OPTIONS (%s)" % ', '.join(opts)

    def diff_options(self, newopts):
        """Compare options lists and generate SQL OPTIONS clause

        :newopts: list of new options
        :return: SQL OPTIONS clause

        Generate ([ADD|SET|DROP key 'value') clauses from two lists in the
        form of 'key=value' strings.
        """
        def to_dict(optlist):
            return dict(opt.split('=', 1) for opt in optlist)

        oldopts = {}
        if len(self.options) > 0:
            oldopts = to_dict(self.options)
        newopts = to_dict(newopts)
        clauses = []
        for key, val in list(newopts.items()):
            if key not in oldopts:
                clauses.append("%s '%s'" % (key, val))
            elif val != oldopts[key]:
                clauses.append("SET %s '%s'" % (key, val))
        for key, val in list(oldopts.items()):
            if key not in newopts:
                clauses.append("DROP %s" % key)
        return clauses and "OPTIONS (%s)" % ', '.join(clauses) or ''

    def alter(self, inobj):
        """Generate SQL to transform an existing object with options

        :param inobj: a YAML map defining the new object
        :return: list of SQL statements
        """
        stmts = super(DbObjectWithOptions, self).alter(inobj)
        newopts = []
        if len(inobj.options) > 0:
            newopts = inobj.options
        diff_opts = self.diff_options(newopts)
        if diff_opts:
            stmts.append("ALTER %s %s %s" % (
                self.objtype, self.identifier(), diff_opts))
        return stmts


class ForeignDataWrapper(DbObjectWithOptions):
    """A foreign data wrapper definition"""

    single_extern_file = True
    catalog = 'pg_foreign_data_wrapper'

    def __init__(self, name, options, description, owner, privileges,
                 handler=None, validator=None,
                 oid=None):
        """Initialize the foreign data wrapper

        :param name-options: see DbObjectWithOptions.__init__ params
        :param description: comment text (from obj_description())
        :param owner: owner name (from rolname via fdwowner)
        :param privileges: access privileges (from fdwacl)
        :param handler: handler function (from fdwhandler)
        :param validator: validator function (from fdwvalidator)
        """
        super(ForeignDataWrapper, self).__init__(name, options)
        self.description = description
        self._init_own_privs(owner, privileges)
        self.handler = handler
        self.validator = validator
        self.servers = {}
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT fdwname AS name, CASE WHEN fdwhandler = 0 THEN NULL
                       ELSE fdwhandler::regproc END AS handler,
                   CASE WHEN fdwvalidator = 0 THEN NULL
                       ELSE fdwvalidator::regproc END AS validator,
                   fdwoptions AS options, rolname AS owner,
                   array_to_string(fdwacl, ',') AS privileges,
                   obj_description(w.oid, 'pg_foreign_data_wrapper') AS
                       description, w.oid
            FROM pg_foreign_data_wrapper w
                JOIN pg_roles r ON (r.oid = fdwowner)
            ORDER BY fdwname"""

    @staticmethod
    def from_map(name, inobj):
        """Initialize an FDW instance from a YAML map

        :param name: FDW name
        :param inobj: YAML map of the FDW
        :return: FDW instance
        """
        obj = ForeignDataWrapper(
            name, inobj.pop('options', {}), inobj.pop('description', None),
            inobj.pop('owner', None), inobj.pop('privileges', []),
            inobj.pop('handler', None), inobj.pop('validator', None))
        obj.fix_privileges()
        obj.set_oldname(inobj)
        return obj

    @property
    def objtype(self):
        return "FOREIGN DATA WRAPPER"

    @property
    def allprivs(self):
        return 'U'

    def to_map(self, db, no_owner, no_privs):
        """Convert wrappers and subsidiary objects to a YAML-suitable format

        :param no_owner: exclude object owner information
        :param no_privs: exclude privilege information
        :return: dictionary
        """
        dct = super(ForeignDataWrapper, self).to_map(db, no_owner, no_privs)
        for attr in ('handler', 'validator'):
            if getattr(self, attr) is None:
                dct.pop(attr)
        srvs = {}
        for srv in self.servers:
            srvs.update(self.servers[srv].to_map(db, no_owner, no_privs))
        dct.update(srvs)
        dct.pop('servers')
        return dct

    @commentable
    @grantable
    @ownable
    def create(self, dbversion=None):
        """Return SQL statements to CREATE the data wrapper

        :return: SQL statements
        """
        clauses = []
        for fnc in ('validator', 'handler'):
            if getattr(self, fnc) is not None:
                clauses.append("%s %s" % (fnc.upper(), getattr(self, fnc)))
        if len(self.options) > 0:
            clauses.append(self.options_clause())
        return ["CREATE FOREIGN DATA WRAPPER %s%s" % (
                quote_id(self.name),
                clauses and '\n    ' + ',\n    '.join(clauses) or '')]


class ForeignDataWrapperDict(DbObjectDict):
    "The collection of foreign data wrappers in a database"

    cls = ForeignDataWrapper

    def from_map(self, inwrappers, newdb):
        """Initialize the dictionary of wrappers by examining the input map

        :param inwrappers: input YAML map defining the data wrappers
        :param newdb: collection of dictionaries defining the database
        """
        for key in inwrappers:
            if not key.startswith('foreign data wrapper '):
                raise KeyError("Unrecognized object type: %s" % key)
            fdw = key[21:]
            inobj = inwrappers[key]
            inservs = {}
            for key in inobj:
                if key.startswith('server '):
                    inservs.update({key: inobj[key]})
            self[fdw] = ForeignDataWrapper.from_map(fdw, inobj)
            newdb.servers.from_map(self[fdw], inservs, newdb)

    def link_refs(self, dbservers):
        """Connect servers to their respective foreign data wrappers

        :param dbservers: dictionary of foreign servers
        """
        for (fdw, srv) in dbservers:
            dbserver = dbservers[(fdw, srv)]
            assert self[fdw]
            wrapper = self[fdw]
            if not hasattr(wrapper, 'servers'):
                wrapper.servers = {}
            wrapper.servers.update({srv: dbserver})


class ForeignServer(DbObjectWithOptions):
    """A foreign server definition"""

    privobjtype = "FOREIGN SERVER"
    keylist = ['wrapper', 'name']
    catalog = 'pg_foreign_server'

    def __init__(self, name, options, description, owner, privileges,
                 wrapper, type=None, version=None,
                 oid=None):
        """Initialize the foreign server

        :param name-options: see DbObjectWithOptions.__init__ params
        :param description: comment text (from obj_description())
        :param owner: owner name (from rolname via srvowner)
        :param privileges: access privileges (from srvacl)
        :param wrapper: foreign data wrapper (from fdwname via srvfdw)
        :param type: server type (from srvtype)
        :param version: version (from srvversion)
        """
        super(ForeignServer, self).__init__(name, options)
        self.description = description
        self._init_own_privs(owner, privileges)
        self.wrapper = wrapper
        self.type = type
        self.version = version
        self.usermaps = {}
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT fdwname AS wrapper, srvname AS name, srvtype AS type,
                   srvversion AS version, srvoptions AS options,
                   rolname AS owner,
                   array_to_string(srvacl, ',') AS privileges, s.oid,
                   obj_description(s.oid, 'pg_foreign_server') AS description
            FROM pg_foreign_server s JOIN pg_roles r ON (r.oid = srvowner)
                 JOIN pg_foreign_data_wrapper w ON (srvfdw = w.oid)
            ORDER BY fdwname, srvname"""

    @staticmethod
    def from_map(name, wrapper, inobj):
        """Initialize a foreign server instance from a YAML map

        :param name: server name
        :param wrapper: FDW name
        :param inobj: YAML map of the server
        :return: foreign server instance
        """
        obj = ForeignServer(
            name, inobj.pop('options', {}), inobj.pop('description', None),
            inobj.pop('owner', None), inobj.pop('privileges', []), wrapper,
            inobj.pop('type', None), inobj.pop('version', None))
        obj.fix_privileges()
        obj.set_oldname(inobj)
        return obj

    @property
    def objtype(self):
        return "SERVER"

    @property
    def allprivs(self):
        return 'U'

    def identifier(self):
        """Returns a full identifier for the foreign server

        :return: string
        """
        return quote_id(self.name)

    def to_map(self, db, no_owner, no_privs):
        """Convert servers and subsidiary objects to a YAML-suitable format

        :param no_owner: exclude server owner information
        :param no_privs: exclude privilege information
        :return: dictionary
        """
        dct = super(ForeignServer, self).to_map(db, no_owner, no_privs)
        for attr in ('type', 'version'):
            if getattr(self, attr) is None:
                dct.pop(attr)
        key = self.extern_key()
        server = {key: dct}
        server[key].pop('usermaps')
        if len(self.usermaps) > 0:
            umaps = {}
            for umap in self.usermaps:
                umaps.update({umap: self.usermaps[umap].to_map(db)})
            server[key]['user mappings'] = umaps

        return server

    @commentable
    @grantable
    @ownable
    def create(self, dbversion=None):
        """Return SQL statements to CREATE the server

        :return: SQL statements
        """
        clauses = []
        options = []
        for opt in ('type', 'version'):
            if getattr(self, opt) is not None:
                clauses.append("%s '%s'" % (opt.upper(), getattr(self, opt)))
        if len(self.options) > 0:
            options.append(self.options_clause())
        return ["CREATE SERVER %s%s\n    FOREIGN DATA WRAPPER %s%s" % (
                quote_id(self.name),
                clauses and ' ' + ' '.join(clauses) or '',
                quote_id(self.wrapper),
                options and '\n    ' + ',\n    '.join(options) or '')]

    def get_implied_deps(self, db):
        deps = super(ForeignServer, self).get_implied_deps(db)
        deps.add(db.fdwrappers[self.wrapper])
        return deps


class ForeignServerDict(DbObjectDict):
    "The collection of foreign servers in a database"

    cls = ForeignServer

    def from_map(self, wrapper, inservers, newdb):
        """Initialize the dictionary of servers by examining the input map

        :param wrapper: associated foreign data wrapper
        :param inservers: input YAML map defining the foreign servers
        :param newdb: collection of dictionaries defining the database
        """
        for key in inservers:
            if not key.startswith('server '):
                raise KeyError("Unrecognized object type: %s" % key)
            srv = key[7:]
            inobj = inservers[key]
            self[(wrapper.name, srv)] = serv = ForeignServer.from_map(
                srv, wrapper.name, inobj)
            if 'user mappings' in inobj:
                newdb.usermaps.from_map(serv, inobj['user mappings'])

    def to_map(self, db, no_owner, no_privs):
        """Convert the server dictionary to a regular dictionary

        :param no_owner: exclude server owner information
        :param no_privs: exclude privilege information
        :return: dictionary

        Invokes the `to_map` method of each server to construct a
        dictionary of foreign servers.
        """
        servers = {}
        for srv in self:
            servers.update(self[srv].to_map(db, no_owner, no_privs))
        return servers

    def link_refs(self, dbusermaps):
        """Connect user mappings to their respective servers

        :param dbusermaps: dictionary of user mappings
        """
        for (fdw, srv, usr) in dbusermaps:
            dbusermap = dbusermaps[(fdw, srv, usr)]
            assert self[(fdw, srv)]
            server = self[(fdw, srv)]
            server.usermaps.update({usr: dbusermap})


class UserMapping(DbObjectWithOptions):
    """A user mapping definition"""

    keylist = ['wrapper', 'server', 'name']
    catalog = 'pg_user_mappings'

    def __init__(self, name, options, wrapper, server,
                 oid=None):
        """Initialize the user mapping

        :param name-options: see DbObjectWithOptions.__init__ params
        :param wrapper: foreign data wrapper (from fdwname via srvfdw)
        :param server: server name (from umserver)
        :param version: version (from srvversion)
        """
        super(UserMapping, self).__init__(name, options)
        self.wrapper = wrapper
        self.server = server
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT fdwname AS wrapper, s.srvname AS server,
                   CASE umuser WHEN 0 THEN 'PUBLIC' ELSE
                   usename END AS name, umoptions AS options, u.umid AS oid
            FROM pg_user_mappings u
                 JOIN pg_foreign_server s ON (u.srvid = s.oid)
                 JOIN pg_foreign_data_wrapper w ON (srvfdw = w.oid)
            ORDER BY fdwname, s.srvname, 3"""

    @staticmethod
    def from_map(name, server, inobj):
        """Initialize a user mapping instance from a YAML map

        :param name: mapping name
        :param server: foreign server map
        :param inobj: YAML map of the user mapping
        :return: user mapping instance
        """
        obj = UserMapping(name, inobj.pop('options', {}), server.wrapper,
                          server.name)
        obj.set_oldname(inobj)
        return obj

    @property
    def objtype(self):
        return "USER MAPPING"

    def extern_key(self):
        """Return the key to be used in external maps for this user mapping

        :return: string
        """
        return self.name

    def identifier(self):
        """Return a full identifier for a user mapping object

        :return: string
        """
        return "FOR %s SERVER %s" % (
            self.name == 'PUBLIC' and 'PUBLIC' or quote_id(self.name),
            quote_id(self.server))

    def create(self, dbversion=None):
        """Return SQL statements to CREATE the user mapping

        :return: SQL statements
        """
        options = []
        if len(self.options) > 0:
            options.append(self.options_clause())
        return ["CREATE USER MAPPING FOR %s\n    SERVER %s%s" % (
                self.name == 'PUBLIC' and 'PUBLIC' or
                quote_id(self.name), quote_id(self.server),
                options and '\n    ' + ',\n    '.join(options) or '')]

    def get_implied_deps(self, db):
        deps = super(UserMapping, self).get_implied_deps(db)
        deps.add(db.fdwrappers[self.wrapper])
        return deps


class UserMappingDict(DbObjectDict):
    "The collection of user mappings in a database"

    cls = UserMapping

    def from_map(self, server, inusermaps):
        """Initialize the dictionary of mappings by examining the input map

        :param server: foreign server associated with mappings
        :param inusermaps: input YAML map defining the user mappings
        """
        for key in inusermaps:
            inobj = inusermaps[key]
            self[(server.wrapper, server.name, key)] = UserMapping.from_map(
                key, server, inobj)

    def to_map(self, db):
        """Convert the user mapping dictionary to a regular dictionary

        :return: dictionary

        Invokes the `to_map` method of each mapping to construct a
        dictionary of user mappings.
        """
        usermaps = {}
        for um in self:
            usermaps.update(self[um].to_map(db))
        return usermaps


class ForeignTable(Table, DbObjectWithOptions):
    """A foreign table definition"""

    privobjtype = "TABLE"
    catalog = 'pg_foreign_table'

    def __init__(self, name, schema, description, owner, privileges,
                 server=None, options={},
                 oid=None):
        """Initialize the foreign table

        :param name-privileges: see DbClass.__init__ params
        :param server: foreign server (from ftserver)
        :param options: table options (from ftoptions)
        """
        super(ForeignTable, self).__init__(name, schema, description, owner,
                                           privileges)
        self.server = server
        self.options = {} if options is None else options
        self.columns = []
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT nspname AS schema, relname AS name, srvname AS server,
                   ftoptions AS options, rolname AS owner,
                   array_to_string(relacl, ',') AS privileges,
                   obj_description(c.oid, 'pg_class') AS description, c.oid
            FROM pg_class c JOIN pg_foreign_table f ON (ftrelid = c.oid)
                 JOIN pg_roles r ON (r.oid = relowner)
                 JOIN pg_foreign_server s ON (ftserver = s.oid)
                 JOIN pg_namespace ON (relnamespace = pg_namespace.oid)
            WHERE relkind = 'f'
              AND (nspname != 'pg_catalog' AND nspname != 'information_schema')
            ORDER BY nspname, relname"""

    @staticmethod
    def from_map(name, schema, inobj):
        """Initialize a foreign table instance from a YAML map

        :param name: foreign table name
        :param name: schema name
        :param inobj: YAML map of the table
        :return: foreign table instance
        """
        obj = ForeignTable(
            name, schema.name, inobj.pop('description', None),
            inobj.pop('owner', None), inobj.pop('privileges', []),
            inobj.pop('server', None), inobj.pop('options', {}))
        obj.fix_privileges()
        return obj

    @property
    def objtype(self):
        return "FOREIGN TABLE"

    def to_map(self, db, opts):
        """Convert a foreign table to a YAML-suitable format

        :param opts: options to include/exclude tables, etc.
        :return: dictionary
        """
        if hasattr(opts, 'excl_tables') and opts.excl_tables \
                and self.name in opts.excl_tables:
            return {}
        if len(self.columns) == 0:
            return {}
        cols = []
        for i in range(len(self.columns)):
            col = self.columns[i].to_map(db, opts.no_privs)
            if col:
                cols.append(col)
        tbl = {'columns': cols, 'server': self.server}
        if self.description is not None:
            tbl.update(description=self.description)
        if not opts.no_owner and self.owner is not None:
            tbl.update(owner=self.owner)
        if len(self.options) > 0:
            tbl.update(options=self.options)
        if not opts.no_privs:
            tbl.update({'privileges': self.map_privs()})

        return tbl

    @grantable
    def create(self, dbversion=None):
        """Return SQL statements to CREATE the foreign table

        :return: SQL statements
        """
        stmts = []
        cols = []
        options = []
        for col in self.columns:
            cols.append("    " + col.add()[0])
        if len(self.options) > 0:
            options.append(self.options_clause())
        stmts.append("CREATE FOREIGN TABLE %s (\n%s)\n    SERVER %s%s" % (
            self.qualname(), ",\n".join(cols), self.server,
            options and '\n    ' + ',\n    '.join(options) or ''))
        if self.owner is not None:
            stmts.append(self.alter_owner())
        if self.description is not None:
            stmts.append(self.comment())
        for col in self.columns:
            if col.description is not None:
                stmts.append(col.comment())
        return stmts

    def drop(self):
        """Return a SQL DROP statement for the foreign table

        :return: SQL statement
        """
        return ["DROP %s %s" % (self.objtype, self.identifier())]

    def alter(self, intable):
        """Generate SQL to transform an existing table

        :param intable: a YAML map defining the new table
        :return: list of SQL statements
        """
        stmts = super(ForeignTable, self).alter(intable)
        if intable.owner is not None:
            if intable.owner != self.owner:
                stmts.append(self.alter_owner(intable.owner))
        stmts.append(self.diff_description(intable))
        return stmts


class ForeignTableDict(ClassDict):
    "The collection of foreign tables in a database"

    cls = ForeignTable

    def _from_catalog(self):
        """Initialize the dictionary of tables by querying the catalogs"""
        for tbl in self.fetch():
            self[tbl.key()] = tbl

    def from_map(self, schema, inobjs, newdb):
        """Initialize the dictionary of tables by converting the input map

        :param schema: schema owning the tables
        :param inobjs: YAML map defining the schema objects
        :param newdb: collection of dictionaries defining the database
        """
        for key in inobjs:
            if not key.startswith('foreign table '):
                raise KeyError("Unrecognized object type: %s" % key)
            ftb = key[14:]
            inobj = inobjs[key]
            self[(schema.name, ftb)] = ftable = ForeignTable.from_map(
                ftb, schema, inobj)
            try:
                newdb.columns.from_map(ftable, inobj['columns'])
            except KeyError as exc:
                exc.args = ("Foreign table '%s' has no columns" % ftb, )
                raise

    def link_refs(self, dbcolumns):
        """Connect columns to their respective foreign tables

        :param dbcolumns: dictionary of columns
        """
        for (sch, tbl) in dbcolumns:
            if (sch, tbl) in self:
                assert isinstance(self[(sch, tbl)], ForeignTable)
                self[(sch, tbl)].columns = dbcolumns[(sch, tbl)]
                for col in dbcolumns[(sch, tbl)]:
                    col._table = self[(sch, tbl)]
