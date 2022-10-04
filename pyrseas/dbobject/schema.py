# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.schema
    ~~~~~~~~~~~~~~~~~~~~~~~

    This defines two classes, Schema and SchemaDict, derived from
    DbObject and DbObjectDict, respectively.
"""
import os

from pyrseas.yamlutil import yamldump
from . import DbObjectDict, DbObject
from . import quote_id, commentable, ownable, grantable
from .dbtype import BaseType, Composite, Domain, Enum, Range
from .table import Table, Sequence
from .view import View, MaterializedView


class Schema(DbObject):
    """A database schema definition, i.e., a named collection of tables,
    views, triggers and other schema objects."""

    keylist = ['name']
    catalog = 'pg_namespace'

    @property
    def allprivs(self):
        return 'UC'

    def __init__(self, name, description=None, owner=None, privileges=[],
                 oldname=None, oid=None):
        """Initialize the schema

        :param name: schema name (from nspname)
        :param description: comment text (from obj_description())
        :param owner: owner name (from rolname via nspowner)
        :param privileges: access privileges (from nspacl)
        :param oldname: previous name of schema
        """
        super(Schema, self).__init__(name, description)
        self._init_own_privs(owner, privileges)
        self.oldname = None

    @staticmethod
    def query(dbversion=None):
        return r"""
            SELECT nspname AS name, rolname AS owner,
                   array_to_string(nspacl, ',') AS privileges,
                   obj_description(n.oid, 'pg_namespace') AS description, n.oid
            FROM pg_namespace n
                 JOIN pg_roles r ON (r.oid = nspowner)
            WHERE nspname NOT IN ('information_schema', 'pg_toast')
                  AND nspname NOT LIKE 'pg_temp\_%'
                  AND nspname NOT LIKE 'pg_toast_temp\_%'
            AND n.oid NOT IN (
                  SELECT objid FROM pg_depend WHERE deptype = 'e'
                  AND classid = 'pg_namespace'::regclass)
            ORDER BY nspname"""

    @staticmethod
    def from_map(name, inobj):
        """Initialize a schema instance from a YAML map

        :param name: schema name
        :param inobj: YAML map of the schema
        :return: schema instance
        """
        obj = Schema(
            name, inobj.pop('description', None), inobj.pop('owner', None),
            inobj.pop('privileges', []))
        obj.fix_privileges()
        obj.set_oldname(inobj)
        return obj

    def extern_dir(self, root='.'):
        """Return the path to a directory to hold the schema objects.

        :return: directory path
        """
        (dir, ext) = os.path.splitext(os.path.join(root,
                                                   self.extern_filename()))
        return dir

    def to_map(self, db, dbschemas, opts):
        """Convert tables, etc., dictionaries to a YAML-suitable format

        :param dbschemas: dictionary of schemas
        :param opts: options to include/exclude schemas/tables, etc.
        :return: dictionary
        """
        if self.name == 'pyrseas':
            return {}
        no_owner = opts.no_owner
        no_privs = opts.no_privs
        schbase = {} if no_owner else {'owner': self.owner}
        if not no_privs:
            schbase.update({'privileges': self.map_privs()})
        if self.description is not None:
            schbase.update(description=self.description)

        schobjs = []
        seltbls = getattr(opts, 'tables', [])
        if hasattr(self, 'tables'):
            for objkey in self.tables:
                if not seltbls or objkey in seltbls:
                    obj = self.tables[objkey]
                    schobjs.append((obj, obj.to_map(db, dbschemas, opts)))

        def mapper(objtypes):
            if hasattr(self, objtypes):
                schemadict = getattr(self, objtypes)
                for objkey in schemadict:
                    if objtypes == 'sequences' or (
                            not seltbls or objkey in seltbls):
                        obj = schemadict[objkey]
                        schobjs.append((obj, obj.to_map(db, opts)))

        for objtypes in ['ftables', 'sequences', 'views', 'matviews']:
            mapper(objtypes)

        def mapper2(objtypes, privs=False):
            if hasattr(self, objtypes):
                schemadict = getattr(self, objtypes)
                for objkey in schemadict:
                    obj = schemadict[objkey]
                    if privs:
                        dct = obj.to_map(db, no_owner, no_privs)
                    else:
                        dct = obj.to_map(db, no_owner)
                    schobjs.append((obj, dct))

        if hasattr(opts, 'tables') and not opts.tables or \
                not hasattr(opts, 'tables'):
            for objtypes in ('conversions', 'collations', 'operators',
                             'operclasses', 'operfams', 'tsconfigs',
                             'tsdicts', 'tsparsers', 'tstempls'):
                mapper2(objtypes)
            for objtypes in ('types', 'domains'):
                mapper2(objtypes, True)
            if hasattr(self, 'functions'):
                for objkey in self.functions:
                    obj = self.functions[objkey]
                    schobjs.append((obj, obj.to_map(db, no_owner, no_privs)))

        # special case for pg_catalog schema
        if self.name == 'pg_catalog' and not schobjs:
            return {}

        if hasattr(self, 'datacopy') and self.datacopy:
            dir = self.extern_dir(opts.data_dir)
            if not os.path.exists(dir):
                os.mkdir(dir)
            for tbl in self.datacopy:
                self.tables[tbl].data_export(dbschemas.dbconn, dir)
            dbschemas.dbconn.commit()

        if opts.multiple_files:
            dir = self.extern_dir(opts.metadata_dir)
            if not os.path.exists(dir):
                os.mkdir(dir)
            filemap = {}
            for obj, objmap in schobjs:
                if objmap is not None:
                    extkey = obj.extern_key()
                    filepath = os.path.join(dir, obj.extern_filename())
                    with open(filepath, 'a') as f:
                        f.write(yamldump({extkey: objmap}))
                    outobj = {extkey:
                              os.path.relpath(filepath, opts.metadata_dir)}
                    filemap.update(outobj)
            # always write the schema YAML file
            filepath = self.extern_filename()
            extkey = self.extern_key()
            with open(os.path.join(opts.metadata_dir, filepath), 'a') as f:
                f.write(yamldump({extkey: schbase}))
            filemap.update(schema=filepath)
            return {extkey: filemap}

        schmap = dict((obj.extern_key(), objmap) for obj, objmap in schobjs
                      if objmap is not None)
        schmap.update(schbase)
        return {self.extern_key(): schmap}

    @commentable
    @grantable
    @ownable
    def create(self, dbversion=None):
        """Return SQL statements to CREATE the schema

        :return: SQL statements
        """
        # special case for --revert
        if self.name == 'pg_catalog':
            return []
        return ["CREATE SCHEMA %s" % quote_id(self.name)]

    def data_import(self, opts):
        """Generate SQL to import data from the tables in this schema

        :param opts: options to include/exclude schemas/tables, etc.
        :return: list of SQL statements
        """
        stmts = []
        if hasattr(self, 'datacopy') and self.datacopy:
            dir = self.extern_dir(opts.data_dir)
            for tbl in self.datacopy:
                stmts.append(self.tables[tbl].data_import(dir))
        return stmts

    def drop(self):
        if self.name not in ('public', 'pg_catalog'):
            return super(Schema, self).drop()
        else:
            return []


PREFIXES = {'domain ': 'types', 'type': 'types', 'table ': 'tables',
            'view ': 'tables', 'sequence ': 'tables',
            'materialized view ': 'tables',
            'function ': 'functions', 'aggregate ': 'functions',
            'operator family ': 'operfams', 'operator class ': 'operclasses',
            'conversion ': 'conversions', 'text search dictionary ': 'tsdicts',
            'text search template ': 'tstempls',
            'text search parser ': 'tsparsers',
            'text search configuration ': 'tsconfigs',
            'foreign table ': 'ftables', 'collation ': 'collations'}
SCHOBJS1 = ['types', 'tables', 'ftables']
SCHOBJS2 = ['collations', 'conversions', 'functions', 'operators',
            'operclasses', 'operfams', 'tsconfigs', 'tsdicts', 'tsparsers',
            'tstempls']


class SchemaDict(DbObjectDict):
    "The collection of schemas in a database.  Minimally, the 'public' schema."

    cls = Schema

    def from_map(self, inmap, newdb):
        """Initialize the dictionary of schemas by converting the input map

        :param inmap: the input YAML map defining the schemas
        :param newdb: collection of dictionaries defining the database

        Starts the recursive analysis of the input map and
        construction of the internal collection of dictionaries
        describing the database objects.
        """
        for key in inmap:
            (objtype, spc, sch) = key.partition(' ')
            if spc != ' ' or objtype != 'schema':
                raise KeyError("Unrecognized object type: %s" % key)
            inobj = inmap[key]
            schema = self[sch] = Schema.from_map(sch, inobj)
            objdict = {}
            for key in sorted(inobj.keys()):
                mapped = False
                for prefix in PREFIXES:
                    if key.startswith(prefix):
                        otype = PREFIXES[prefix]
                        if otype not in objdict:
                            objdict[otype] = {}
                        objdict[otype].update({key: inobj[key]})
                        mapped = True
                        break
                # Needs separate processing because it overlaps
                # operator classes and operator families
                if not mapped and key.startswith('operator '):
                    otype = 'operators'
                    if otype not in objdict:
                        objdict[otype] = {}
                    objdict[otype].update({key: inobj[key]})
                    mapped = True
                elif key == 'oldname':
                    inobj.pop(key)
                    mapped = True
                if not mapped and key != 'schema':
                    raise KeyError("Expected typed object, found '%s'" % key)

            for objtype in SCHOBJS1:
                if objtype in objdict:
                    subobjs = getattr(newdb, objtype)
                    subobjs.from_map(schema, objdict[objtype], newdb)
            for objtype in SCHOBJS2:
                if objtype in objdict:
                    subobjs = getattr(newdb, objtype)
                    subobjs.from_map(schema, objdict[objtype])

    def link_refs(self, db, datacopy):
        """Connect various schema objects to their respective schemas

        :param db: dictionary of dictionaries of all objects
        :param datacopy: dictionary of data copying info
        """
        def link_one(targdict, objtype, objkeys, subtype=None):
            schema = self[objkeys[0]]
            if subtype is None:
                subtype = objtype
            if not hasattr(schema, subtype):
                setattr(schema, subtype, {})
            objdict = getattr(schema, subtype)
            key = objkeys[1] if len(objkeys) == 2 else objkeys[1:]
            objdict.update({key: targdict[objkeys]})

        targ = db.types
        for keys in targ:
            dbtype = targ[keys]
            if isinstance(dbtype, Domain):
                link_one(targ, 'types', keys, 'domains')
            elif isinstance(dbtype, (Enum, Composite, BaseType, Range)):
                link_one(targ, 'types', keys)
        targ = db.tables
        for keys in targ:
            table = targ[keys]
            type_ = 'tables'
            if isinstance(table, Table):
                link_one(targ, type_, keys)
            elif isinstance(table, Sequence):
                link_one(targ, type_, keys, 'sequences')
            elif isinstance(table, MaterializedView):
                link_one(targ, type_, keys, 'matviews')
            elif isinstance(table, View):
                link_one(targ, type_, keys, 'views')
        targ = db.functions
        for keys in targ:
            link_one(targ, 'functions', keys)
        for objtype in ['operators', 'operclasses', 'operfams', 'conversions',
                        'tsconfigs', 'tsdicts', 'tsparsers', 'tstempls',
                        'ftables', 'collations']:
            targ = getattr(db, objtype)
            for keys in targ:
                link_one(targ, objtype, keys)
        for key in datacopy:
            if not key.startswith('schema '):
                raise KeyError("Unrecognized object type: %s" % key)
            sch = key[7:]
            if sch not in self:
                continue
            schema = self[sch]
            if not hasattr(schema, 'datacopy'):
                schema.datacopy = []
            for tbl in datacopy[key]:
                if hasattr(schema, 'tables') and tbl in schema.tables:
                    schema.datacopy.append(tbl)

    def to_map(self, db, opts):
        """Convert the schema dictionary to a regular dictionary

        :param opts: options to include/exclude schemas/tables, etc.
        :return: dictionary

        Invokes the `to_map` method of each schema to construct a
        dictionary of schemas.
        """
        schemas = {}
        selschs = getattr(opts, 'schemas', [])
        for sch in self:
            if not selschs or sch in selschs:
                if hasattr(opts, 'excl_schemas') and opts.excl_schemas \
                        and sch in opts.excl_schemas:
                    continue
                schemas.update(self[sch].to_map(db, self, opts))

        return schemas

    def data_import(self, opts):
        """Iterate over schemas with tables to be imported

        :param opts: options to include/exclude schemas/tables, etc.
        :return: list of SQL statements
        """
        return [self[sch].data_import(opts) for sch in self]
