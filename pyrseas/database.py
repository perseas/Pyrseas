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

from pyrseas.lib.dbconn import DbConnection

from pyrseas.yamlutil import yamldump
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
        schs = self.fetchall("SELECT current_schemas(false)")
        addschs = [sch for sch in schs[0]["current_schemas"] if sch != "public"]
        srch_path = "pg_catalog"
        if addschs:
            srch_path += ", " + ", ".join(addschs)
        self.execute("set search_path to %s" % srch_path)
        self.commit()
        self._version = self.conn.info.server_version

    @property
    def version(self):
        "The server's version number"
        if self.conn is None:
            self.connect()
        return self._version


class Database(object):
    """A database definition, from its catalogs and/or a YAML spec."""

    class Dicts(object):
        """A holder for dictionaries (maps) describing a database"""

        def __init__(self, dbconn=None, single_db=False):
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

            # Populate a map from system catalog to the respective dict
            self._catalog_map = {}
            for _, d in self.all_dicts(single_db):
                if d.cls.catalog is not None:
                    self._catalog_map[d.cls.catalog] = d

            # Map from objects extkey to their (dict name, key)
            self._extkey_map = {}

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
                return self._extkey_map[extkey]
            except KeyError:
                # TODO: Likely it's the first time we call this function so
                # let's warm up the cache. But we should really define the life
                # cycle of this object as trying and catching KeyError on it is
                # *very* expensive!
                for _, d in self.all_dicts():
                    for obj in list(d.values()):
                        self._extkey_map[obj.extern_key()] = obj

                return self._extkey_map[extkey]

        def all_dicts(self, non_empty=False):
            """Iterate over the DbObjectDict-derived dictionaries returning
            an ordered list of tuples (dict name, DbObjectDict object).

            :param non_empty: do not include empty dicts

            :return: list of tuples
            """
            rv = []
            for attr in self.__dict__:
                d = getattr(self, attr)
                if non_empty and len(d) == 0:
                    continue
                if isinstance(d, DbObjectDict):
                    # skip ColumnDict as not needed for dependency tracking
                    # and internally has lists, not objects
                    if not isinstance(d, ColumnDict):
                        rv.append((attr, d))

            # first return the dicts for non-schema objects, then the
            # others, each group sorted alphabetically.
            rv.sort(key=lambda pair: (issubclass(pair[1].cls, DbSchemaObject),
                                      pair[1].cls.__name__))

            return rv

        def dbobjdict_from_catalog(self, catalog):
            """Given a catalog name, return corresponding DbObjectDict

            :param catalog: full name of a pg_ catalog
            :return: DbObjectDict object
            """
            return self._catalog_map.get(catalog)

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
            langs = [lang["lanname"] for lang in self.dbconn.fetchall(
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
        db.functions.link_refs(db.types)
        db.fdwrappers.link_refs(db.servers)
        db.servers.link_refs(db.usermaps)
        db.ftables.link_refs(db.columns)
        db.types.link_refs(db.columns, db.constraints, db.functions)
        db.constraints.link_refs(db)

    def _build_dependency_graph(self, db, dbconn):
        """Build the dependency graph of the database objects

        :param db: dictionary of dictionary of all objects
        :param dbconn: a DbConnection object
        """
        alldeps = defaultdict(list)

        # This query wanted to be simple. it got complicated because
        # we don't handle indexes together with the other pg_class
        # but in their own pg_index place (so fetch i1, i2)
        # "Normal" dependencies, but excluding system objects
        # (objid < 16384 and refobjid < 16384)
        query = """SELECT DISTINCT
                          CASE WHEN i1.indexrelid IS NOT NULL
                          THEN 'pg_index'::regclass
                          ELSE classid::regclass END AS class_name, objid,
                          CASE WHEN i2.indexrelid IS NOT NULL
                          THEN 'pg_index'::regclass
                          ELSE refclassid::regclass END AS refclass, refobjid
                   FROM pg_depend
                        LEFT JOIN pg_index i1 ON classid = 'pg_class'::regclass
                             AND objid = i1.indexrelid
                        LEFT JOIN pg_index i2
                             ON refclassid = 'pg_class'::regclass
                             AND refobjid = i2.indexrelid
                   WHERE deptype = 'n'
                   AND NOT (objid < 16384 AND refobjid < 16384)"""
        for r in dbconn.fetchall(query):
            alldeps[r['class_name'], r['objid']].append(
                (r['refclass'], r['refobjid']))

        # The dependencies across views is not in pg_depend. We have to
        # parse the rewrite rule.  "ev_class >= 16384" is to exclude
        # system views.
        query = r"""SELECT DISTINCT 'pg_class' AS class_name, ev_class,
                          CASE WHEN depid[1] = 'relid' THEN 'pg_class'
                               WHEN depid[1] = 'funcid' THEN 'pg_proc'
                               END AS refclass, depid[2]::oid AS refobjid
                   FROM (SELECT ev_class, regexp_matches(ev_action,
                                ':(relid|funcid)\s+(\d+)', 'g') AS depid
                         FROM pg_rewrite
                         WHERE rulename = '_RETURN'
                         AND ev_class >= 16384) x
                         LEFT JOIN pg_class c
                              ON (depid[1], depid[2]::oid) = ('relid', c.oid)
                         LEFT JOIN pg_namespace cs ON cs.oid = relnamespace
                         LEFT JOIN pg_proc p
                              ON (depid[1], depid[2]::oid) = ('funcid', p.oid)
                         LEFT JOIN pg_namespace ps ON ps.oid = pronamespace
                   WHERE ev_class <> depid[2]::oid
                   AND coalesce(cs.nspname, ps.nspname)
                         NOT IN ('information_schema', 'pg_catalog')"""
        for r in dbconn.fetchall(query):
            alldeps[r['class_name'], r['ev_class']].append(
                (r['refclass'], r['refobjid']))

        # Add the dependencies between a table and other objects through the
        # columns defaults
        query = """SELECT 'pg_class' AS class_name, adrelid,
                          d.refclassid::regclass, d.refobjid
                   FROM pg_attrdef ad JOIN pg_depend d
                        ON classid = 'pg_attrdef'::regclass AND objid = ad.oid
                        AND deptype = 'n'"""
        for r in dbconn.fetchall(query):
            alldeps[r['class_name'], r['adrelid']].append(
                (r['refclassid'], r['refobjid']))

        for (stbl, soid), deps in list(alldeps.items()):
            sdict = db.dbobjdict_from_catalog(stbl)
            if sdict is None or len(sdict) == 0:
                continue
            src = sdict.by_oid.get(soid)
            if src is None:
                continue
            for ttbl, toid in deps:
                tdict = db.dbobjdict_from_catalog(ttbl)
                if tdict is None or len(tdict) == 0:
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

    def from_catalog(self, single_db=False):
        """Populate the database objects by querying the catalogs

        :param single_db: populating only this database?

        The `db` holder is populated by various DbObjectDict-derived
        classes by querying the catalogs.  A dependency graph is
        constructed by querying the pg_depend catalog.  The objects in
        the dictionary are then linked to related objects, e.g.,
        columns are linked to the tables they belong.
        """
        self.db = self.Dicts(self.dbconn, single_db)
        self._build_dependency_graph(self.db, self.dbconn)
        if self.dbconn.conn:
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
        self.ndb.extensions.from_map(input_extens, self.ndb)
        self.ndb.languages.from_map(input_langs)
        self.ndb.schemas.from_map(input_schemas, self.ndb)
        self.ndb.casts.from_map(input_casts, self.ndb)
        self.ndb.fdwrappers.from_map(input_fdws, self.ndb)
        self.ndb.eventtrigs.from_map(input_evttrigs, self.ndb)
        self._link_refs(self.ndb)

    def map_from_dir(self):
        """Read the database maps starting from the metadata directory

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

        :return: a YAML-suitable dictionary (without any Python objects)
        """
        if not self.db:
            self.from_catalog(True)

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

    def diff_map(self, input_map, quote_reserved=True):
        """Generate SQL to transform an existing database

        :param input_map: a YAML map defining the new database
        :param quote_reserved: fetch reserved words
        :return: list of SQL statements

        Compares the existing database definition, as fetched from the
        catalogs, to the input YAML map and generates SQL statements
        to transform the database into the one represented by the
        input.
        """
        from .dbobject.table import Table

        if not self.db:
            self.from_catalog()
        opts = self.config['options']
        if opts.schemas:
            schlist = ['schema ' + sch for sch in opts.schemas]
            for sch in list(input_map.keys()):
                if sch not in schlist and sch.startswith('schema '):
                    del input_map[sch]
            self._trim_objects(opts.schemas)

        # quote_reserved is only set to False by most tests
        if quote_reserved:
            fetch_reserved_words(self.dbconn)

        self.from_map(input_map)
        if opts.revert:
            (self.db, self.ndb) = (self.ndb, self.db)
            del self.ndb.schemas['pg_catalog']
            self.db.languages.dbconn = self.dbconn

        # First sort the objects in the new db in dependency order
        new_objs = []
        for _, d in self.ndb.all_dicts():
            pairs = list(d.items())
            pairs.sort()
            new_objs.extend(list(map(itemgetter(1), pairs)))

        new_objs = self.dep_sorted(new_objs, self.ndb)

        # Then generate the sql for all the objects, walking in dependency
        # order over all the db objects

        stmts = []
        for new in new_objs:
            d = self.db.dbobjdict_from_catalog(new.catalog)
            old = d.get(new.key())
            if old is not None:
                stmts.append(old.alter(new))
            else:
                stmts.append(new.create_sql(self.dbconn.version))

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
        for _, d in self.db.all_dicts():
            pairs = list(d.items())
            pairs.sort
            old_objs.extend(list(map(itemgetter(1), pairs)))
        old_objs = self.dep_sorted(old_objs, self.db)
        old_objs.reverse()

        # Drop the objects that don't appear in the new db
        for old in old_objs:
            d = self.ndb.dbobjdict_from_catalog(old.catalog)
            if isinstance(old, Table):
                new = d.get(old.key())
                if new is not None:
                    stmts.extend(old.alter_drop_columns(new))
            if not getattr(old, '_nodrop', False) and old.key() not in d:
                stmts.extend(old.drop())

        if 'datacopy' in self.config:
            opts.data_dir = self.config['files']['data_path']
            stmts.append(self.ndb.schemas.data_import(opts))

        stmts = [s for s in flatten(stmts)]
        funcs = False
        for s in stmts:
            if "LANGUAGE sql" in s and (
                    s.startswith("CREATE FUNCTION ") or
                    s.startswith("CREATE OR REPLACE FUNCTION ")):
                funcs = True
                break
        if funcs:
            stmts.insert(0, "SET check_function_bodies = false")

        return stmts

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
