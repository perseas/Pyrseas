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
from pyrseas.lib.dbconn import DbConnection
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

    def __init__(self, dbname, user=None, pswd=None, host=None, port=None):
        """Initialize the database

        :param dbname: database name
        :param user: user name
        :param pswd: user password
        :param host: host name
        :param port: host port number
        """
        self.dbconn = CatDbConnection(dbname, user, pswd, host, port)
        self.db = None

    def _link_refs(self, db):
        """Link related objects"""
        db.languages.link_refs(db.functions)
        db.schemas.link_refs(db.types, db.tables, db.functions, db.operators,
                             db.operfams, db.operclasses, db.conversions,
                             db.tsconfigs, db.tsdicts, db.tsparsers,
                             db.tstempls, db.ftables, db.collations)
        db.tables.link_refs(db.columns, db.constraints, db.indexes,
                            db.rules, db.triggers)
        db.fdwrappers.link_refs(db.servers)
        db.servers.link_refs(db.usermaps)
        db.ftables.link_refs(db.columns)
        db.types.link_refs(db.columns, db.constraints, db.functions)

    def _trim_objects(self, schemas):
        """Remove unwanted schema objects

        :param schemas: list of schemas to keep
        """
        for objtype in ['types', 'tables', 'constraints', 'indexes',
                        'functions', 'operators', 'operclasses', 'operfams',
                        'rules', 'triggers', 'conversions', 'tstempls',
                        'tsdicts', 'tsparsers', 'tsconfigs', 'extensions',
                        'collations']:
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
        for key in list(input_map.keys()):
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
            else:
                raise KeyError("Expected typed object, found '%s'" % key)
        self.ndb.extensions.from_map(input_extens, langs, self.ndb)
        self.ndb.languages.from_map(input_langs)
        self.ndb.schemas.from_map(input_schemas, self.ndb)
        self.ndb.casts.from_map(input_casts, self.ndb)
        self.ndb.fdwrappers.from_map(input_fdws, self.ndb)
        self._link_refs(self.ndb)

    def to_map(self, schemas=[], tables=[], exclude_schemas=[],
            exclude_tables=[], no_owner=False, no_privs=False):
        """Convert the db maps to a single hierarchy suitable for YAML

        :param schemas: list of schemas to be output
        :param tables: list of tables to be output
        :param exclude_schemas:
            list of schemas to be excluded from output, even those listed in
            ``schemas``
        :param exclude_tables:
            list of tables to be excluded from output, even those listed in
            ``tables``
        :param no_owner: exclude object owner information
        :param no_privs: exclude privilege information
        :return: a YAML-suitable dictionary (without Python objects)
        """
        if not self.db:
            self.from_catalog()
        dbmap = self.db.extensions.to_map(no_owner)
        dbmap.update(self.db.languages.to_map(no_owner, no_privs))
        dbmap.update(self.db.casts.to_map())
        dbmap.update(self.db.fdwrappers.to_map(no_owner, no_privs))
        dbmap.update(self.db.schemas.to_map(no_owner, no_privs))
        # trim the map of schemas/tables not selected

        if schemas:
            schemakeys = set('schema ' + sch for sch in schemas)
            for sch in list(dbmap.keys()):
                if sch not in schemakeys:
                    del dbmap[sch]

        if exclude_schemas:
            schemakeys = set('schema ' + sch for sch in exclude_schemas)
            for sch in list(dbmap.keys()):
                if sch in schemakeys:
                    del dbmap[sch]

        if tables or exclude_tables:
            ktablist = ['table ' + tbl for tbl in tables]
            exktablist = ['table ' + tbl for tbl in exclude_tables]
            for sch in list(dbmap.keys()):
                if sch.startswith('schema '):
                    for key in list(dbmap[sch].keys()):
                        if key == 'description':
                            continue
                        if key.startswith('sequence '):
                            if 'owner_table' in dbmap[sch][key] and \
                                    dbmap[sch][key]['owner_table'] in tables:
                                continue
                        if exktablist and key in exktablist:
                            del dbmap[sch][key]
                        if ktablist and key not in ktablist:
                            del dbmap[sch][key]
                    if not dbmap[sch]:
                        del dbmap[sch]

        # special case for pg_catalog schema
        if 'schema pg_catalog' in dbmap:
            if not [k for k in list(dbmap['schema pg_catalog'].keys()) if
                     k not in ('description', 'owner', 'privileges')]:
                del dbmap['schema pg_catalog']
        return dbmap

    def diff_map(self, input_map, schemas=[]):
        """Generate SQL to transform an existing database

        :param input_map: a YAML map defining the new database
        :param schemas: list of schemas to diff
        :return: list of SQL statements

        Compares the existing database definition, as fetched from the
        catalogs, to the input YAML map and generates SQL statements
        to transform the database into the one represented by the
        input.
        """
        if not self.db:
            self.from_catalog()
        if schemas:
            self._trim_objects(schemas)
        langs = None
        if self.dbconn.version >= 90100:
            langs = [lang[0] for lang in self.dbconn.fetchall(
                    "SELECT tmplname FROM pg_pltemplate")]
        self.from_map(input_map, langs)
        stmts = self.db.extensions.diff_map(self.ndb.extensions)
        stmts.append(self.db.languages.diff_map(self.ndb.languages))
        stmts.append(self.db.schemas.diff_map(self.ndb.schemas))
        stmts.append(self.db.types.diff_map(self.ndb.types))
        stmts.append(self.db.functions.diff_map(self.ndb.functions))
        stmts.append(self.db.operators.diff_map(self.ndb.operators))
        stmts.append(self.db.operfams.diff_map(self.ndb.operfams))
        stmts.append(self.db.operclasses.diff_map(self.ndb.operclasses))
        stmts.append(self.db.tables.diff_map(self.ndb.tables))
        stmts.append(self.db.constraints.diff_map(self.ndb.constraints))
        stmts.append(self.db.indexes.diff_map(self.ndb.indexes))
        stmts.append(self.db.columns.diff_map(self.ndb.columns))
        stmts.append(self.db.triggers.diff_map(self.ndb.triggers))
        stmts.append(self.db.rules.diff_map(self.ndb.rules))
        stmts.append(self.db.conversions.diff_map(self.ndb.conversions))
        stmts.append(self.db.tsdicts.diff_map(self.ndb.tsdicts))
        stmts.append(self.db.tstempls.diff_map(self.ndb.tstempls))
        stmts.append(self.db.tsparsers.diff_map(self.ndb.tsparsers))
        stmts.append(self.db.tsconfigs.diff_map(self.ndb.tsconfigs))
        stmts.append(self.db.casts.diff_map(self.ndb.casts))
        stmts.append(self.db.collations.diff_map(self.ndb.collations))
        stmts.append(self.db.fdwrappers.diff_map(self.ndb.fdwrappers))
        stmts.append(self.db.servers.diff_map(self.ndb.servers))
        stmts.append(self.db.usermaps.diff_map(self.ndb.usermaps))
        stmts.append(self.db.ftables.diff_map(self.ndb.ftables))
        stmts.append(self.db.operators._drop())
        stmts.append(self.db.operclasses._drop())
        stmts.append(self.db.operfams._drop())
        stmts.append(self.db.functions._drop())
        stmts.append(self.db.types._drop())
        stmts.append(self.db.extensions._drop())
        stmts.append(self.db.schemas._drop())
        stmts.append(self.db.servers._drop())
        stmts.append(self.db.fdwrappers._drop())
        stmts.append(self.db.languages._drop())
        return [s for s in flatten(stmts)]
