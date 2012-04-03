# -*- coding: utf-8 -*-
"""
    pyrseas.extenddb
    ~~~~~~~~~~~~~~~~

    An `ExtendDatabase` is initialized with a DbConnection object.  It
    consists of two "dictionary" container objects, each holding
    various dictionary objects.  The `db` Dicts object (inherited from
    its parent class), defines the database schemas, including their
    tables and other objects, by querying the system catalogs.  The
    `edb` ExtDicts object defines the extension schemas and the
    configuration objects based on the ext_map supplied to the `apply`
    method.
"""
from pyrseas.database import Database
from pyrseas.dbobject.language import Language
from pyrseas.extend.schema import ExtSchemaDict
from pyrseas.extend.table import ExtClassDict
from pyrseas.extend.denorm import ExtDenormDict
from pyrseas.extend.column import CfgColumnDict
from pyrseas.extend.function import CfgFunctionDict
from pyrseas.extend.trigger import CfgTriggerDict
from pyrseas.extend.audit import CfgAuditColumnDict


class ExtendDatabase(Database):
    """A database that is to be extended"""

    class ExtDicts(object):
        """A holder for dictionaries (maps) describing extensions"""

        def __init__(self):
            """Initialize the various DbExtensionDict-derived dictionaries"""
            self.schemas = ExtSchemaDict()
            self.tables = ExtClassDict()
            self.columns = CfgColumnDict()
            self.functions = CfgFunctionDict()
            self.triggers = CfgTriggerDict()
            self.auditcols = CfgAuditColumnDict()
            self.denorms = ExtDenormDict()

        def _link_refs(self):
            """Link related objects"""
            self.schemas.link_refs(self.tables)
            self.tables.link_refs(self.denorms)

        def _link_current(self, db):
            """Link extension objects to current catalog objects"""
            self.current = db
            self.schemas.link_current(db.schemas)
            self.tables.link_current(db.tables)
            self.denorms.link_current(db.constraints)

        def add_lang(self, lang):
            """Add a language if not already present

            :param lang: the possibly new language
            """
            if lang not in self.current.languages:
                self.current.languages[lang] = Language(name=lang)

    def from_extmap(self, ext_map):
        """Populate the extension objects from the input extension map

        :param ext_map: a YAML map defining the desired extensions

        The `edb` holder is populated by various
        DbExtensionDict-derived classes by traversing the YAML
        extension map. The objects in the dictionary are then linked
        to related objects, e.g., tables are linked to the schemas
        they belong.
        """
        self.edb = self.ExtDicts()
        ext_schemas = {}
        for key in list(ext_map.keys()):
            if key == 'extender':
                self._from_cfgmap(ext_map[key])
            elif key.startswith('schema '):
                ext_schemas.update({key: ext_map[key]})
            else:
                raise KeyError("Expected typed object, found '%s'" % key)
        self.edb.schemas.from_map(ext_schemas, self.edb)
        self.edb._link_refs()
        self.edb._link_current(self.db)

    def _from_cfgmap(self, cfg_map):
        """Populate configuration objects from the input configuration map

        :param cfg_map: a YAML map defining extension configuration

        The extensions dictionary is populated by various
        DbExtensionDict-derived classes by traversing the YAML
        configuration map.
        """
        for key in list(cfg_map.keys()):
            if key == 'columns':
                self.edb.columns.from_map(cfg_map[key])
            elif key == 'functions':
                self.edb.functions.from_map(cfg_map[key])
            elif key == 'triggers':
                self.edb.triggers.from_map(cfg_map[key])
            elif key == 'audit_columns':
                self.edb.auditcols.from_map(cfg_map[key])
            else:
                raise KeyError("Expected typed object, found '%s'" % key)

    def apply(self, ext_map):
        """Apply extensions to an existing database

        :param ext_map: a YAML map defining the desired extensions

        Merges an existing database definition, as fetched from the
        catalogs, with an input YAML defining extensions on various
        objects and an optional configuration map or the predefined
        configuration.
        """
        if not self.db:
            self.from_catalog()
        self.from_extmap(ext_map)
        for sch in self.edb.schemas:
            self.edb.schemas[sch].apply(self.edb)
        return self.to_map()
