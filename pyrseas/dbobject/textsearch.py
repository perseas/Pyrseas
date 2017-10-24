# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.textsearch
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~

    This defines eight classes: TSConfiguration, TSDictionary,
    TSParser and TSTemplate derived from DbSchemaObject, and
    TSConfigurationDict, TSDictionaryDict, TSParserDict and
    TSTemplateDict derived from DbObjectDict.
"""
from . import DbObjectDict, DbSchemaObject
from . import commentable, ownable, split_schema_obj


class TSConfiguration(DbSchemaObject):
    """A text search configuration definition"""

    keylist = ['schema', 'name']
    single_extern_file = True
    catalog = 'pg_ts_config'

    def __init__(self, name, schema, description, owner, parser,
                 oid=None):
        """Initialize the configuration

        :param name: configuration name (from cfgname)
        :param description: comment text (from obj_description())
        :param schema: schema name (from cfgnamespace)
        :param owner: owner name (from rolname via cfgowner)
        :param parser: parser name (from prsname via cfgparser)
        """
        super(TSConfiguration, self).__init__(name, schema, description)
        self._init_own_privs(owner, [])
        self.parser = parser
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT nc.nspname AS schema, cfgname AS name,
                   rolname AS owner, np.nspname || '.' || prsname AS parser,
                   obj_description(c.oid, 'pg_ts_config') AS description, c.oid
            FROM pg_ts_config c JOIN pg_roles r ON (r.oid = cfgowner)
                 JOIN pg_ts_parser p ON (cfgparser = p.oid)
                 JOIN pg_namespace nc ON (cfgnamespace = nc.oid)
                 JOIN pg_namespace np ON (prsnamespace = np.oid)
            WHERE nc.nspname != 'pg_catalog'
              AND nc.nspname != 'information_schema'
            ORDER BY nc.nspname, cfgname"""

    @staticmethod
    def from_map(name, schema, inobj):
        """Initialize a configuration instance from a YAML map

        :param name: configuration name
        :param name: schema map
        :param inobj: YAML map of the configuration
        :return: configuration instance
        """
        obj = TSConfiguration(
            name, schema.name, inobj.pop('description', None),
            inobj.pop('owner', None), inobj.pop('parser', None))
        obj.set_oldname(inobj)
        return obj

    @property
    def objtype(self):
        return "TEXT SEARCH CONFIGURATION"

    def to_map(self, db, no_owner):
        """Convert a text search configuration to a YAML-suitable format

        :return: dictionary
        """
        dct = super(TSConfiguration, self).to_map(db, no_owner)
        if '.' in self.parser:
            (sch, pars) = self.parser.split('.')
            if sch == self.schema:
                dct['parser'] = pars
        return dct

    @commentable
    @ownable
    def create(self, dbversion=None):
        """Return SQL statements to CREATE the configuration

        :return: SQL statements
        """
        clauses = []
        clauses.append("PARSER = %s" % self.parser)
        return ["CREATE TEXT SEARCH CONFIGURATION %s (\n    %s)" % (
                self.qualname(), ',\n    '.join(clauses))]

    def get_implied_deps(self, db):
        deps = super(TSConfiguration, self).get_implied_deps(db)
        deps.add(db.tsparsers[split_schema_obj(self.parser, self.schema)])
        return deps


class TSConfigurationDict(DbObjectDict):
    "The collection of text search configurations in a database"

    cls = TSConfiguration

    def from_map(self, schema, inconfigs):
        """Initialize the dictionary of configs by examining the input map

        :param schema: schema owning the configurations
        :param inconfigs: input YAML map defining the configurations
        """
        for key in inconfigs:
            if not key.startswith('text search configuration '):
                raise KeyError("Unrecognized object type: %s" % key)
            tsc = key[26:]
            inobj = inconfigs[key]
            self[(schema.name, tsc)] = TSConfiguration.from_map(
                tsc, schema, inobj)


class TSDictionary(DbSchemaObject):
    """A text search dictionary definition"""

    keylist = ['schema', 'name']
    single_extern_file = True
    catalog = 'pg_ts_dict'

    def __init__(self, name, schema, description, owner, template, options,
                 oid=None):
        """Initialize the dictionary

        :param name: dictionary name (from dictname)
        :param schema: schema name (from dictnamespace)
        :param description: comment text (from obj_description())
        :param owner: owner name (from rolname via dictowner)
        :param template: template name (from dicttemplate)
        :param options: initialization option string (from dictinitoption)
        """
        super(TSDictionary, self).__init__(name, schema, description)
        self._init_own_privs(owner, [])
        self.template = template
        self.options = options
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT nspname AS schema, dictname AS name, rolname AS owner,
                   tmplname AS template, dictinitoption AS options,
                   obj_description(d.oid, 'pg_ts_dict') AS description, d.oid
            FROM pg_ts_dict d JOIN pg_ts_template t ON (dicttemplate = t.oid)
                 JOIN pg_roles r ON (r.oid = dictowner)
                 JOIN pg_namespace n ON (dictnamespace = n.oid)
            WHERE nspname != 'pg_catalog' AND nspname != 'information_schema'
            ORDER BY nspname, dictname"""

    @staticmethod
    def from_map(name, schema, inobj):
        """Initialize a dictionary instance from a YAML map

        :param name: dictionary name
        :param name: schema map
        :param inobj: YAML map of the dictionary
        :return: dictionary instance
        """
        obj = TSDictionary(
            name, schema.name, inobj.pop('description', None),
            inobj.pop('owner', None), inobj.pop('template', None),
            inobj.pop('options', None))
        obj.set_oldname(inobj)
        return obj

    @property
    def objtype(self):
        return "TEXT SEARCH DICTIONARY"

    @commentable
    @ownable
    def create(self, dbversion=None):
        """Return SQL statements to CREATE the dictionary

        :return: SQL statements
        """
        clauses = []
        clauses.append("TEMPLATE = %s" % self.template)
        if self.options is not None:
            clauses.append(self.options)
        return ["CREATE TEXT SEARCH DICTIONARY %s (\n    %s)" % (
                self.qualname(), ',\n    '.join(clauses))]


class TSDictionaryDict(DbObjectDict):
    "The collection of text search dictionaries in a database"

    cls = TSDictionary

    def from_map(self, schema, indicts):
        """Initialize the dictionary of dictionaries by examining the input map

        :param schema: schema owning the dictionaries
        :param indicts: input YAML map defining the dictionaries
        """
        for key in indicts:
            if not key.startswith('text search dictionary '):
                raise KeyError("Unrecognized object type: %s" % key)
            tsd = key[23:]
            inobj = indicts[key]
            self[(schema.name, tsd)] = TSDictionary.from_map(
                tsd, schema, inobj)


class TSParser(DbSchemaObject):
    """A text search parser definition"""

    keylist = ['schema', 'name']
    single_extern_file = True
    catalog = 'pg_ts_parser'

    def __init__(self, name, schema, description, start, gettoken, end,
                 headline, lextypes,
                 oid=None):
        """Initialize the parser

        :param name: parser name (from prsname)
        :param schema: schema name (from prsnamespace)
        :param description: comment text (from obj_description())
        :param start: startup function (from prsstart)
        :param gettoken: next-token function (from prstoken)
        :param end: shutdown function (from prsend)
        :param headline: headline function (from prsheadline)
        :param lextypes: lextype function (from prslextype)
        """
        super(TSParser, self).__init__(name, schema, description)
        self._init_own_privs(None, [])
        self.start = start
        self.gettoken = gettoken
        self.end = end
        self.headline = headline
        self.lextypes = lextypes
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT nspname AS schema, prsname AS name,
                   prsstart::regproc AS start, prstoken::regproc AS gettoken,
                   prsend::regproc AS end, prslextype::regproc AS lextypes,
                   prsheadline::regproc AS headline,
                   obj_description(p.oid, 'pg_ts_parser') AS description, p.oid
            FROM pg_ts_parser p JOIN pg_namespace n ON (prsnamespace = n.oid)
            WHERE nspname != 'pg_catalog' AND nspname != 'information_schema'
            ORDER BY nspname, prsname"""

    @staticmethod
    def from_map(name, schema, inobj):
        """Initialize a parser instance from a YAML map

        :param name: parser name
        :param name: schema map
        :param inobj: YAML map of the parser
        :return: parser instance
        """
        obj = TSParser(name, schema.name, inobj.pop('description', None),
                       inobj.pop('start', None), inobj.pop('gettoken', None),
                       inobj.pop('end', None), inobj.pop('headline', None),
                       inobj.pop('lextypes', None))
        obj.set_oldname(inobj)
        return obj

    @property
    def objtype(self):
        return "TEXT SEARCH PARSER"

    @commentable
    @ownable
    def create(self, dbversion=None):
        """Return SQL statements to CREATE the parser

        :return: SQL statements
        """
        clauses = []
        for attr in ['start', 'gettoken', 'end', 'lextypes']:
            clauses.append("%s = %s" % (attr.upper(), getattr(self, attr)))
        if self.headline is not None:
            clauses.append("HEADLINE = %s" % self.headline)
        return ["CREATE TEXT SEARCH PARSER %s (\n    %s)" % (
                self.qualname(), ',\n    '.join(clauses))]


class TSParserDict(DbObjectDict):
    "The collection of text search parsers in a database"

    cls = TSParser

    def from_map(self, schema, inparsers):
        """Initialize the dictionary of parsers by examining the input map

        :param schema: schema owning the parsers
        :param inparsers: input YAML map defining the parsers
        """
        for key in inparsers:
            if not key.startswith('text search parser '):
                raise KeyError("Unrecognized object type: %s" % key)
            tsp = key[19:]
            inobj = inparsers[key]
            self[(schema.name, tsp)] = TSParser.from_map(tsp, schema, inobj)


class TSTemplate(DbSchemaObject):
    """A text search template definition"""

    keylist = ['schema', 'name']
    single_extern_file = True
    catalog = 'pg_ts_template'

    def __init__(self, name, schema, description, init, lexize,
                 oid=None):
        """Initialize the template

        :param name: template name (from tmplname)
        :param schema: schema name (from tmplnamespace)
        :param description: comment text (from obj_description())
        :param init: initialization function (from tmplinit)
        :param lexize: lexize function (from tmpllexize)
        """
        super(TSTemplate, self).__init__(name, schema, description)
        self._init_own_privs(None, [])
        self.init = init
        self.lexize = lexize
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT nspname AS schema, tmplname AS name, p.oid,
                   tmplinit::regproc AS init, tmpllexize::regproc AS lexize,
                   obj_description(p.oid, 'pg_ts_template') AS description
            FROM pg_ts_template p
                 JOIN pg_namespace n ON (tmplnamespace = n.oid)
            WHERE nspname != 'pg_catalog' AND nspname != 'information_schema'
            ORDER BY nspname, tmplname"""

    @staticmethod
    def from_map(name, schema, inobj):
        """Initialize a template instance from a YAML map

        :param name: template name
        :param name: schema map
        :param inobj: YAML map of the template
        :return: template instance
        """
        obj = TSTemplate(name, schema.name, inobj.pop('description', None),
                         inobj.pop('init', None), inobj.pop('lexize', None))
        obj.set_oldname(inobj)
        return obj

    @property
    def objtype(self):
        return "TEXT SEARCH TEMPLATE"

    @commentable
    def create(self, dbversion=None):
        """Return SQL statements to CREATE the template

        :return: SQL statements
        """
        clauses = []
        if self.init is not None:
            clauses.append("INIT = %s" % self.init)
        clauses.append("LEXIZE = %s" % self.lexize)
        return ["CREATE TEXT SEARCH TEMPLATE %s (\n    %s)" % (
                self.qualname(), ',\n    '.join(clauses))]


class TSTemplateDict(DbObjectDict):
    "The collection of text search templates in a database"

    cls = TSTemplate

    def from_map(self, schema, intemplates):
        """Initialize the dictionary of templates by examining the input map

        :param schema: schema owning the templates
        :param intemplates: input YAML map defining the templates
        """
        for key in intemplates:
            if not key.startswith('text search template '):
                raise KeyError("Unrecognized object type: %s" % key)
            tst = key[21:]
            inobj = intemplates[key]
            self[(schema.name, tst)] = TSTemplate.from_map(tst, schema, inobj)
