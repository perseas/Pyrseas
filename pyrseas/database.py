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
from collections import defaultdict

import yaml

from pyrseas.yamlutil import yamldump
from pyrseas.lib.dbconn import DbConnection
from pyrseas.dbobject import fetch_reserved_words, DbObjectDict
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
            for attr in dir(self):
                d = getattr(self, attr)
                if not isinstance(d, DbObjectDict):
                    continue

                # It is none for the attribute, but the dependencies are on
                # the table so it's fine.
                if d.cls.catalog_table is None:
                    continue

                self._table_map[d.cls.catalog_table] = d

        def dict_from_table(self, catalog_table):
            return self._table_map.get(catalog_table)

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
        db.functions.link_refs(db.eventtrigs)
        db.fdwrappers.link_refs(db.servers)
        db.servers.link_refs(db.usermaps)
        db.ftables.link_refs(db.columns)
        db.types.link_refs(db.columns, db.constraints, db.functions)

    def _build_depends(self, db, dbconn):
        """Build the dependency graph of the database objects
        """
        deps = defaultdict(list)
        for r in dbconn.fetchall("""
                SELECT classid::regclass, objid,
                       refclassid::regclass, refobjid
                FROM pg_depend
                WHERE deptype = 'n'
                """):
            deps[r[0], r[1]].append((r[2], r[3]))

        for (stbl, soid), deps in deps.iteritems():
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
                for obj, val in objmap.items():
                    if isinstance(val, dict):
                        dirpath = ''
                        for schobj, fpath in val.items():
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

        dbmap = self.db.extensions.to_map(opts)
        dbmap.update(self.db.languages.to_map(opts))
        dbmap.update(self.db.casts.to_map(opts))
        dbmap.update(self.db.fdwrappers.to_map(opts))
        dbmap.update(self.db.eventtrigs.to_map(opts))
        if 'datacopy' in self.config:
            opts.data_dir = self.config['files']['data_path']
            if not os.path.exists(opts.data_dir):
                mkdir_parents(opts.data_dir)
        dbmap.update(self.db.schemas.to_map(opts))

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
            for sch in input_map.keys():
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
            self.db.languages.dbconn = self.dbconn

        changes = {}
        # TODO: this ordering is only for testing: force 'domain' to be
        # emitted before 'function' to test the topo sort
        for attr in sorted(dir(self.db)):
            d = getattr(self.db, attr)
            if not isinstance(d, DbObjectDict):
                continue
            # TODO: drop this check: it's only to test with a subset of all
            # the classes
            if not hasattr(d, '_diff_map'):
                continue
            changes.update(d._diff_map(getattr(self.ndb, attr)))

        stmts = []
        for v in changes.itervalues():
            stmts.extend(v)

        stmts.append(self.db.operators._drop())
        stmts.append(self.db.operclasses._drop())
        stmts.append(self.db.operfams._drop())
        stmts.append(self.db.functions._drop())
        stmts.append(self.db.types._drop())
        stmts.append(self.db.schemas._drop())
        stmts.append(self.db.servers._drop())
        stmts.append(self.db.fdwrappers._drop())
        stmts.append(self.db.languages._drop())
        stmts.append(self.db.extensions._drop())
        if 'datacopy' in self.config:
            opts.data_dir = self.config['files']['data_path']
            stmts.append(self.ndb.schemas.data_import(opts))
        return [s for s in flatten(stmts)]
