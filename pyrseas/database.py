# -*- coding: utf-8 -*-
"""
    pyrseas.database
    ~~~~~~~~~~~~~~~~

    A `Database` is initialized with a DbConnection object.  It
    consists of one or two `Dicts` objects, each holding various
    dictionary objects.  The `db` Dicts object defines the database
    schemas, including their tables and other objects, by querying the
    system catalogs.  The `ndb` Dicts object defines the schemas based
    on the `input_map` supplied to the `from_map` method.
"""
import os
import sys
from operator import itemgetter
from collections import defaultdict, deque

import yaml

from pyrseas.yamlutil import yamldump
from pyrseas.lib.dbconn import DbConnection
from pyrseas.dbobject import fetch_reserved_words, DbObjectDict, DbSchemaObject
from pyrseas.dbobject.language import LanguageDict
from pyrseas.dbobject.cast import CastDict
from pyrseas.dbobject.schema import SchemaDict
from pyrseas.dbobject.dbtype import TypeDict
from pyrseas.dbobject.table import ClassDict
from pyrseas.dbobject.column import ColumnDict
from pyrseas.dbobject.constraint import ConstraintDict
from pyrseas.dbobject.index import IndexDict
from pyrseas.dbobject.function import ProcDict
from pyrseas.dbobject.operator import OperatorDict
from pyrseas.dbobject.operclass import OperatorClassDict
from pyrseas.dbobject.operfamily import OperatorFamilyDict
from pyrseas.dbobject.rule import RuleDict
from pyrseas.dbobject.trigger import TriggerDict
from pyrseas.dbobject.conversion import ConversionDict
from pyrseas.dbobject.textsearch import TSConfigurationDict, TSDictionaryDict
from pyrseas.dbobject.textsearch import TSParserDict, TSTemplateDict
from pyrseas.dbobject.foreign import ForeignDataWrapperDict
from pyrseas.dbobject.foreign import ForeignServerDict, UserMappingDict
from pyrseas.dbobject.foreign import ForeignTableDict
from pyrseas.dbobject.extension import ExtensionDict
from pyrseas.dbobject.collation import CollationDict
from pyrseas.dbobject.eventtrig import EventTriggerDict


def flatten(lst):
    "Flatten a list possibly containing lists to a single list"
    for elem in lst:
        if isinstance(elem, list) and not isinstance(elem, str):
            for subelem in flatten(elem):
                yield subelem
        else:
            yield elem


class CatDbConnection(DbConnection):
    """A database connection, specialized for querying catalogs"""

    def connect(self):
        """Connect to the database"""
        super(CatDbConnection, self).connect()
        try:
            self.execute("set search_path to public, pg_catalog")
        except:
            self.rollback()
            self.execute("set search_path to pg_catalog")
        self.commit()
        self._version = self.conn.server_version

    @property
    def version(self):
        "The server's version number"
        return self._version


class Database(object):
    """A database definition, from its catalogs and/or a YAML spec."""

    class Dicts(object):
        """A holder for dictionaries (maps) describing a database"""

        def __init__(self, dbconn=None):
            """Initialize the various DbObjectDict-derived dictionaries

            :param dbconn: a DbConnection object
            """
            self.schemas = SchemaDict(dbconn)
            self.extensions = ExtensionDict(dbconn)
            self.languages = LanguageDict(dbconn)
            self.casts = CastDict(dbconn)
            self.types = TypeDict(dbconn)
            self.tables = ClassDict(dbconn)
            self.columns = ColumnDict(dbconn)
            self.constraints = ConstraintDict(dbconn)
            self.indexes = IndexDict(dbconn)
            self.functions = ProcDict(dbconn)
            self.operators = OperatorDict(dbconn)
            self.operclasses = OperatorClassDict(dbconn)
            self.operfams = OperatorFamilyDict(dbconn)
            self.rules = RuleDict(dbconn)
            self.triggers = TriggerDict(dbconn)
            self.conversions = ConversionDict(dbconn)
            self.tstempls = TSTemplateDict(dbconn)
            self.tsdicts = TSDictionaryDict(dbconn)
            self.tsparsers = TSParserDict(dbconn)
            self.tsconfigs = TSConfigurationDict(dbconn)
            self.fdwrappers = ForeignDataWrapperDict(dbconn)
            self.servers = ForeignServerDict(dbconn)
            self.usermaps = UserMappingDict(dbconn)
            self.ftables = ForeignTableDict(dbconn)
            self.collations = CollationDict(dbconn)
            self.eventtrigs = EventTriggerDict(dbconn)

            # Populate a map from catalog table map to the dict responsible
            self._table_map = {}
            for _, d in self.alldicts():
                # It is none for the attribute, but the dependencies are on
                # the table so it's fine.
                if d.cls.catalog_table is None:
                    continue

                self._table_map[d.cls.catalog_table] = d

            self._by_extkey = {}
            """
            Map from objects extkey to their (dict name, key)
            """

        def _get_by_extkey(self, extkey):
            """Return any database item from its extkey

            Note: probably doesn't work for all the objects, e.g. constraints
            may clash because two in different tables have different extkeys.
            However this shouldn't matter as such objects are generated as part
            of the containing one and they should be returned by the
            `get_implied_deps()` implementation of specific classes (which
            would look for the object in by key in the right dict instead,
            (e.g.  check `Domain.get_implied_deps()` implementation.

            """
            try:
                return self._by_extkey[extkey]
            except KeyError:
                # TODO: Likely it's the first time we call this function so
                # let's warm up the cache. But we should really define the life
                # cycle of this object as trying and catching KeyError on it is
                # *very* expensive!
                for _, d in self.alldicts():
                    for obj in list(d.values()):
                        self._by_extkey[obj.extern_key()] = obj

                return self._by_extkey[extkey]

        def alldicts(self):
            """Iterate over all the database objects dict

            :return: list of (dict name, dict) for every database dict.
            """
            rv = []
            for attr in self.__dict__:
                d = getattr(self, attr)
                if isinstance(d, DbObjectDict):
                    # skip this as not needed for dependency tracking
                    # and internally has lists, not objects
                    if isinstance(d, ColumnDict):
                        continue
                    rv.append((attr, d))

            # first return the dicts for non-schema objects, then the
            # others, each group sorted alphabetically.
            rv.sort(key=lambda pair: (issubclass(pair[1].cls, DbSchemaObject),
                                      pair[1].cls.__name__))

            return rv

        def dict_from_table(self, catalog_table):
            return self._table_map.get(catalog_table)

        def find_type(self, name):
            """Return a db type given a qualname

            Note that tables and views are types too.
            """
            rv = self.types.find(name)
            if rv is not None:
                return rv

            rv = self.tables.find(name)
            return rv

    def __init__(self, config):
        """Initialize the database

        :param config: configuration dictionary
        """
        db = config['database']
        self.dbconn = CatDbConnection(db['dbname'], db['username'],
                                      db['password'], db['host'], db['port'])
        self.db = None
        self.config = config

    def _link_refs(self, db):
        """Link related objects"""
        langs = []
        if self.dbconn.version >= 90100:
            langs = [lang[0] for lang in self.dbconn.fetchall(
                """SELECT lanname FROM pg_language l
                     JOIN pg_depend p ON (l.oid = p.objid)
                    WHERE deptype = 'e' """)]
        db.languages.link_refs(db.functions, langs)
        copycfg = {}
        if 'datacopy' in self.config:
            copycfg = self.config['datacopy']
        db.schemas.link_refs(db, copycfg)
        db.tables.link_refs(db.columns, db.constraints, db.indexes, db.rules,
                            db.triggers)
        db.functions.link_refs(db.types, db.eventtrigs)
        db.fdwrappers.link_refs(db.servers)
        db.servers.link_refs(db.usermaps)
        db.ftables.link_refs(db.columns)
        db.types.link_refs(db.columns, db.constraints, db.functions)
        db.constraints.link_refs(db)

    def _build_depends(self, db, dbconn):
        """Build the dependency graph of the database objects
        """
        deps = defaultdict(list)
        # This query wanted to be simple. it got complicated because:
        # 1) we don't handle indexes together with the other pg_class
        #    but in their own pg_index place (so fetch i1, i2)
        # 2) what point two?
        for r in dbconn.fetchall("""
                SELECT
                    CASE WHEN i1.indexrelid IS NOT NULL
                        THEN 'pg_index'::regclass
                        ELSE classid::regclass END,
                    objid,
                    CASE
                        WHEN i2.indexrelid IS NOT NULL
                            THEN 'pg_index'::regclass
                        ELSE refclassid::regclass END,
                    refobjid
                FROM pg_depend
                LEFT JOIN pg_index i1
                    ON classid = 'pg_class'::regclass
                    AND objid = i1.indexrelid
                LEFT JOIN pg_index i2
                    ON refclassid = 'pg_class'::regclass
                    AND refobjid = i2.indexrelid
                WHERE deptype = 'n'
                """):
            deps[r[0], r[1]].append((r[2], r[3]))

        # The dependencies across views is not in pg_depend. We have to parse
        # the rewrite rule (TODO: only tested on PG 9.3):
        for r in dbconn.fetchall("""
                select distinct 'pg_class', ev_class,
                    case when depid[1] = 'relid' then 'pg_class'
                         when depid[1] = 'funcid' then 'pg_proc'
                    end, depid[2]::oid
                from (
                    select ev_class,
                        regexp_matches(ev_action,
                            ':(relid|funcid)\s+(\d+)', 'g')
                            as depid
                    from pg_rewrite
                    where rulename = '_RETURN') x

                left join pg_class c
                    on (depid[1], depid[2]::oid) = ('relid', c.oid)
                left join pg_namespace cs on cs.oid = relnamespace

                left join pg_proc p
                    on (depid[1], depid[2]::oid) = ('funcid', p.oid)
                left join pg_namespace ps on ps.oid = pronamespace

                where ev_class <> depid[2]::oid
                and coalesce(cs.nspname, ps.nspname)
                    not in ('information_schema', 'pg_catalog')
                """):
            deps[r[0], r[1]].append((r[2], r[3]))

        # Add the dependencies between a table and other objects through the
        # columns defaults
        for r in dbconn.fetchall("""
                select 'pg_class', adrelid,
                    d.refclassid::regclass, d.refobjid
                from pg_attrdef ad
                join pg_depend d
                    on classid = 'pg_attrdef'::regclass
                    and objid = ad.oid
                    and deptype = 'n'
                """):
            deps[r[0], r[1]].append((r[2], r[3]))

        for (stbl, soid), deps in list(deps.items()):
            sdict = db.dict_from_table(stbl)
            if sdict is None:
                continue
            src = sdict.by_oid.get(soid)
            if src is None:
                continue
            for ttbl, toid in deps:
                tdict = db.dict_from_table(ttbl)
                if tdict is None:
                    continue
                tgt = tdict.by_oid.get(toid)
                if tgt is None:
                    continue
                src.depends_on.append(tgt)

    def _trim_objects(self, schemas):
        """Remove unwanted schema objects

        :param schemas: list of schemas to keep
        """
        for objtype in ['types', 'tables', 'constraints', 'indexes',
                        'functions', 'operators', 'operclasses', 'operfams',
                        'rules', 'triggers', 'conversions', 'tstempls',
                        'tsdicts', 'tsparsers', 'tsconfigs', 'extensions',
                        'collations', 'eventtrigs']:
            objdict = getattr(self.db, objtype)
            for obj in list(objdict.keys()):
                # obj[0] is the schema name in all these dicts
                if obj[0] not in schemas:
                    del objdict[obj]
        for sch in list(self.db.schemas.keys()):
            if sch not in schemas:
                del self.db.schemas[sch]
        # exclude database-wide objects
        self.db.languages = LanguageDict()
        self.db.casts = CastDict()

    def from_catalog(self):
        """Populate the database objects by querying the catalogs

        The `db` holder is populated by various DbObjectDict-derived
        classes by querying the catalogs. The objects in the
        dictionary are then linked to related objects, e.g., columns
        are linked to the tables they belong.
        """
        self.db = self.Dicts(self.dbconn)
        if self.dbconn.conn:
            self._build_depends(self.db, self.dbconn)
            self.dbconn.conn.close()
        self._link_refs(self.db)

    def from_map(self, input_map, langs=None):
        """Populate the new database objects from the input map

        :param input_map: a YAML map defining the new database
        :param langs: list of language templates

        The `ndb` holder is populated by various DbObjectDict-derived
        classes by traversing the YAML input map. The objects in the
        dictionary are then linked to related objects, e.g., columns
        are linked to the tables they belong.
        """
        self.ndb = self.Dicts()
        input_schemas = {}
        input_extens = {}
        input_langs = {}
        input_casts = {}
        input_fdws = {}
        input_ums = {}
        input_evttrigs = {}
        for key in input_map:
            if key.startswith('schema '):
                input_schemas.update({key: input_map[key]})
            elif key.startswith('extension '):
                input_extens.update({key: input_map[key]})
            elif key.startswith('language '):
                input_langs.update({key: input_map[key]})
            elif key.startswith('cast '):
                input_casts.update({key: input_map[key]})
            elif key.startswith('foreign data wrapper '):
                input_fdws.update({key: input_map[key]})
            elif key.startswith('user mapping for '):
                input_ums.update({key: input_map[key]})
            elif key.startswith('event trigger '):
                input_evttrigs.update({key: input_map[key]})
            else:
                raise KeyError("Expected typed object, found '%s'" % key)
        self.ndb.extensions.from_map(input_extens, langs, self.ndb)
        self.ndb.languages.from_map(input_langs)
        self.ndb.schemas.from_map(input_schemas, self.ndb)
        self.ndb.casts.from_map(input_casts, self.ndb)
        self.ndb.fdwrappers.from_map(input_fdws, self.ndb)
        self.ndb.eventtrigs.from_map(input_evttrigs, self.ndb)
        self._link_refs(self.ndb)

    def map_from_dir(self):
        """Read the database maps starting from metadata directory

        :return: dictionary
        """
        metadata_dir = self.config['files']['metadata_path']
        if not os.path.isdir(metadata_dir):
            sys.exit("Metadata directory '%s' doesn't exist" % metadata_dir)

        def load(subdir, obj):
            with open(os.path.join(subdir, obj), 'r') as f:
                objmap = yaml.safe_load(f)
            return objmap if isinstance(objmap, dict) else {}

        inmap = {}
        for entry in os.listdir(metadata_dir):
            if entry.endswith('.yaml'):
                if entry.startswith('database.'):
                    continue
                if not entry.startswith('schema.'):
                    inmap.update(load(metadata_dir, entry))
            else:
                # skip over unknown files/dirs
                if not entry.startswith('schema.'):
                    continue
                # read schema.xxx.yaml first
                schmap = load(metadata_dir, entry + '.yaml')
                assert(len(schmap) == 1)
                key = list(schmap.keys())[0]
                inmap.update({key: {}})
                subdir = os.path.join(metadata_dir, entry)
                if os.path.isdir(subdir):
                    for schobj in os.listdir(subdir):
                        schmap[key].update(load(subdir, schobj))
                inmap.update(schmap)

        return inmap

    def to_map(self):
        """Convert the db maps to a single hierarchy suitable for YAML

        :return: a YAML-suitable dictionary (without Python objects)
        """
        if not self.db:
            self.from_catalog()

        opts = self.config['options']

        def mkdir_parents(dir):
            head, tail = os.path.split(dir)
            if head and not os.path.isdir(head):
                mkdir_parents(head)
            if tail:
                os.mkdir(dir)

        if opts.multiple_files:
            opts.metadata_dir = self.config['files']['metadata_path']
            if not os.path.exists(opts.metadata_dir):
                mkdir_parents(opts.metadata_dir)
            dbfilepath = os.path.join(opts.metadata_dir, 'database.%s.yaml' %
                                      self.dbconn.dbname)
            if os.path.exists(dbfilepath):
                with open(dbfilepath, 'r') as f:
                    objmap = yaml.safe_load(f)
                for obj, val in list(objmap.items()):
                    if isinstance(val, dict):
                        dirpath = ''
                        for schobj, fpath in list(val.items()):
                            filepath = os.path.join(opts.metadata_dir, fpath)
                            if os.path.exists(filepath):
                                os.remove(filepath)
                                if schobj == 'schema':
                                    (dirpath, ext) = os.path.splitext(filepath)
                        if os.path.exists(dirpath):
                            os.rmdir(dirpath)
                    else:
                        filepath = os.path.join(opts.metadata_dir, val)
                        if (os.path.exists(filepath)):
                            os.remove(filepath)

        dbmap = self.db.extensions.to_map(self.db, opts)
        dbmap.update(self.db.languages.to_map(self.db, opts))
        dbmap.update(self.db.casts.to_map(self.db, opts))
        dbmap.update(self.db.fdwrappers.to_map(self.db, opts))
        dbmap.update(self.db.eventtrigs.to_map(self.db, opts))
        if 'datacopy' in self.config:
            opts.data_dir = self.config['files']['data_path']
            if not os.path.exists(opts.data_dir):
                mkdir_parents(opts.data_dir)
        dbmap.update(self.db.schemas.to_map(self.db, opts))

        if opts.multiple_files:
            with open(dbfilepath, 'w') as f:
                f.write(yamldump(dbmap))

        return dbmap

    def diff_map(self, input_map):
        """Generate SQL to transform an existing database

        :param input_map: a YAML map defining the new database
        :return: list of SQL statements

        Compares the existing database definition, as fetched from the
        catalogs, to the input YAML map and generates SQL statements
        to transform the database into the one represented by the
        input.
        """
        if not self.db:
            self.from_catalog()
        opts = self.config['options']
        if opts.schemas:
            schlist = ['schema ' + sch for sch in opts.schemas]
            for sch in list(input_map.keys()):
                if sch not in schlist and sch.startswith('schema '):
                    del input_map[sch]
            self._trim_objects(opts.schemas)

        if opts.quote_reserved:
            fetch_reserved_words(self.dbconn)

        langs = None
        if self.dbconn.version >= 90100:
            langs = [lang[0] for lang in self.dbconn.fetchall(
                "SELECT tmplname FROM pg_pltemplate")]
        self.from_map(input_map, langs)
        if opts.revert:
            (self.db, self.ndb) = (self.ndb, self.db)
            del self.ndb.schemas['pg_catalog']
            self.db.languages.dbconn = self.dbconn

        # First sort the objects in the new db in dependency order
        new_objs = []
        for _, d in self.ndb.alldicts():
            pairs = list(d.items())
            pairs.sort()
            new_objs.extend(list(map(itemgetter(1), pairs)))

        new_objs = self.dep_sorted(new_objs, self.ndb)

        # Then generate the sql for all the objects, walking in dependency
        # order over all the db objects

        stmts = []
        for new in new_objs:
            d = self.db.dict_from_table(new.catalog_table)
            old = d.get(new.key())
            if old is not None:
                stmts.append(old.alter(new))
            else:
                stmts.append(new.create_sql())

                # Check if the object just created was renamed, in which case
                # don't try to delete the original one
                if getattr(new, 'oldname', None):
                    try:
                        origname, new.name = new.name, new.oldname
                        oldkey = new.key()
                    finally:
                        new.name = origname
                    # Intentionally raising KeyError as tested e.g. in
                    # test_bad_rename_view -- ok Joe?
                    old = d[oldkey]
                    old._nodrop = True

        # Order the old database objects in reverse dependency order
        old_objs = []
        for _, d in self.db.alldicts():
            pairs = list(d.items())
            pairs.sort
            old_objs.extend(list(map(itemgetter(1), pairs)))
        old_objs = self.dep_sorted(old_objs, self.db)
        old_objs.reverse()

        # Drop the objects that don't appear in the new db
        for old in old_objs:
            d = self.ndb.dict_from_table(old.catalog_table)
            if not getattr(old, '_nodrop', False) and old.key() not in d:
                stmts.extend(old.drop())

        if 'datacopy' in self.config:
            opts.data_dir = self.config['files']['data_path']
            stmts.append(self.ndb.schemas.data_import(opts))

        return [s for s in flatten(stmts)]

    def dep_sorted(self, objs, db):
        """Sort `objs` in order of dependency.

        The function implements the classic Kahn 62 algorighm, see
        <http://en.wikipedia.org/wiki/Topological_sorting>.
        """
        # List of objects to return
        L = []

        # Collect the graph edges.
        # Note that our "dependencies" are sort of backwards compared to the
        # terms used in the algorithm (an edge in the algo would be from the
        # schema to the table, we have the table depending on the schema)
        ein = defaultdict(set)
        eout = defaultdict(deque)
        for obj in objs:
            for dep in obj.get_deps(db):
                eout[dep].append(obj)
                ein[obj].add(dep)

        # The objects with no dependency to start with
        S = deque()
        for obj in objs:
            if obj not in ein:
                S.append(obj)

        while S:
            # Objects with no dependencies can be emitted
            obj = S.popleft()
            L.append(obj)

            # Delete the edges and check if depending objects have no
            # dependency now
            while eout[obj]:
                ch = eout[obj].popleft()
                ein[ch].remove(obj)
                if not ein[ch]:
                    del ein[ch]
                    S.append(ch)

            del eout[obj]   # remove the empty set

        assert bool(ein) == bool(eout)
        if not ein:
            return L
        else:
            # is it possible? How do we deal with that?
            raise Exception("the objects dependencies graph has loops")
