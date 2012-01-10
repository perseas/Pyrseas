# -*- coding: utf-8 -*-
"""
    pyrseas.textsearch
    ~~~~~~~~~~~~~~~~~~

    This defines eight classes: TSConfiguration, TSDictionary,
    TSParser and TSTemplate derived from DbSchemaObject, and
    TSConfigurationDict, TSDictionaryDict, TSParserDict and
    TSTemplateDict derived from DbObjectDict.
"""
from pyrseas.dbobject import DbObjectDict, DbSchemaObject


class TSConfiguration(DbSchemaObject):
    """A text search configuration definition"""

    keylist = ['schema', 'name']
    objtype = "TEXT SEARCH CONFIGURATION"

    def to_map(self):
        """Convert a text search configuration to a YAML-suitable format

        :return: dictionary
        """
        dct = self._base_map()
        if '.' in self.parser:
            (sch, pars) = self.parser.split('.')
            if sch == self.schema:
                dct['parser'] = pars
        return {self.extern_key(): dct}

    def create(self):
        """Return SQL statements to CREATE the configuration

        :return: SQL statements
        """
        clauses = []
        clauses.append("PARSER = %s" % self.parser)
        stmts = ["CREATE TEXT SEARCH CONFIGURATION %s (\n    %s)" % (
                self.qualname(), ',\n    '.join(clauses))]
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts


class TSConfigurationDict(DbObjectDict):
    "The collection of text search configurations in a database"

    cls = TSConfiguration
    query = \
        """SELECT nc.nspname AS schema, cfgname AS name,
                  np.nspname || '.' || prsname AS parser,
                  obj_description(c.oid, 'pg_ts_config') AS description
           FROM pg_ts_config c
                JOIN pg_ts_parser p ON (cfgparser = p.oid)
                JOIN pg_namespace nc ON (cfgnamespace = nc.oid)
                JOIN pg_namespace np ON (prsnamespace = np.oid)
           WHERE (nc.nspname != 'pg_catalog'
                  AND nc.nspname != 'information_schema')
           ORDER BY nc.nspname, cfgname"""

    def from_map(self, schema, inconfigs):
        """Initialize the dictionary of configs by examining the input map

        :param schema: schema owning the configurations
        :param inconfigs: input YAML map defining the configurations
        """
        for key in inconfigs.keys():
            if not key.startswith('text search configuration '):
                raise KeyError("Unrecognized object type: %s" % key)
            tsc = key[26:]
            self[(schema.name, tsc)] = config = TSConfiguration(
                schema=schema.name, name=tsc)
            inconfig = inconfigs[key]
            if inconfig:
                for attr, val in inconfig.items():
                    setattr(config, attr, val)
                if 'oldname' in inconfig:
                    config.oldname = inconfig['oldname']
                    del inconfig['oldname']
                if 'description' in inconfig:
                    config.description = inconfig['description']

    def diff_map(self, inconfigs):
        """Generate SQL to transform existing configurations

        :param input_map: a YAML map defining the new configurations
        :return: list of SQL statements

        Compares the existing configuration definitions, as fetched from the
        catalogs, to the input map and generates SQL statements to
        transform the configurations accordingly.
        """
        stmts = []
        # check input configurations
        for (sch, tsc) in inconfigs.keys():
            intsc = inconfigs[(sch, tsc)]
            # does it exist in the database?
            if (sch, tsc) in self:
                stmts.append(self[(sch, tsc)].diff_map(intsc))
            else:
                # check for possible RENAME
                if hasattr(intsc, 'oldname'):
                    oldname = intsc.oldname
                    try:
                        stmts.append(self[oldname].rename(intsc.name))
                        del self[oldname]
                    except KeyError as exc:
                        exc.args = ("Previous name '%s' for configuration "
                                   "'%s' not found" % (oldname, intsc.name), )
                        raise
                else:
                    # create new configuration
                    stmts.append(intsc.create())
        # check database configurations
        for (sch, tsc) in self.keys():
            # if missing, drop it
            if (sch, tsc) not in inconfigs:
                stmts.append(self[(sch, tsc)].drop())
        return stmts


class TSDictionary(DbSchemaObject):
    """A text search dictionary definition"""

    keylist = ['schema', 'name']
    objtype = "TEXT SEARCH DICTIONARY"

    def create(self):
        """Return SQL statements to CREATE the dictionary

        :return: SQL statements
        """
        clauses = []
        clauses.append("TEMPLATE = %s" % self.template)
        if hasattr(self, 'options'):
            clauses.append(self.options)
        stmts = ["CREATE TEXT SEARCH DICTIONARY %s (\n    %s)" % (
                self.qualname(), ',\n    '.join(clauses))]
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts


class TSDictionaryDict(DbObjectDict):
    "The collection of text search dictionaries in a database"

    cls = TSDictionary
    query = \
        """SELECT nspname AS schema, dictname AS name,
                  tmplname AS template, dictinitoption AS options,
                  obj_description(d.oid, 'pg_ts_dict') AS description
           FROM pg_ts_dict d JOIN pg_ts_template t ON (dicttemplate = t.oid)
                JOIN pg_namespace n ON (dictnamespace = n.oid)
           WHERE (nspname != 'pg_catalog' AND nspname != 'information_schema')
           ORDER BY nspname, dictname"""

    def from_map(self, schema, indicts):
        """Initialize the dictionary of dictionaries by examining the input map

        :param schema: schema owning the dictionaries
        :param indicts: input YAML map defining the dictionaries
        """
        for key in indicts.keys():
            if not key.startswith('text search dictionary '):
                raise KeyError("Unrecognized object type: %s" % key)
            tsd = key[23:]
            self[(schema.name, tsd)] = tsdict = TSDictionary(
                schema=schema.name, name=tsd)
            indict = indicts[key]
            if indict:
                for attr, val in indict.items():
                    setattr(tsdict, attr, val)
                if 'oldname' in indict:
                    tsdict.oldname = indict['oldname']
                    del indict['oldname']
                if 'description' in indict:
                    tsdict.description = indict['description']

    def diff_map(self, indicts):
        """Generate SQL to transform existing dictionaries

        :param input_map: a YAML map defining the new dictionaries
        :return: list of SQL statements

        Compares the existing dictionary definitions, as fetched from the
        catalogs, to the input map and generates SQL statements to
        transform the dictionaries accordingly.
        """
        stmts = []
        # check input dictionaries
        for (sch, tsd) in indicts.keys():
            intsd = indicts[(sch, tsd)]
            # does it exist in the database?
            if (sch, tsd) in self:
                stmts.append(self[(sch, tsd)].diff_map(intsd))
            else:
                # check for possible RENAME
                if hasattr(intsd, 'oldname'):
                    oldname = intsd.oldname
                    try:
                        stmts.append(self[oldname].rename(intsd.name))
                        del self[oldname]
                    except KeyError as exc:
                        exc.args = ("Previous name '%s' for dictionary '%s' "
                                   "not found" % (oldname, intsd.name), )
                        raise
                else:
                    # create new dictionary
                    stmts.append(intsd.create())
        # check database dictionaries
        for (sch, tsd) in self.keys():
            # if missing, drop it
            if (sch, tsd) not in indicts:
                stmts.append(self[(sch, tsd)].drop())
        return stmts


class TSParser(DbSchemaObject):
    """A text search parser definition"""

    keylist = ['schema', 'name']
    objtype = "TEXT SEARCH PARSER"

    def create(self):
        """Return SQL statements to CREATE the parser

        :return: SQL statements
        """
        clauses = []
        for attr in ['start', 'gettoken', 'end', 'lextypes']:
            clauses.append("%s = %s" % (attr.upper(), getattr(self, attr)))
        if hasattr(self, 'headline'):
            clauses.append("HEADLINE = %s" % self.headline)
        stmts = ["CREATE TEXT SEARCH PARSER %s (\n    %s)" % (
                self.qualname(), ',\n    '.join(clauses))]
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts


class TSParserDict(DbObjectDict):
    "The collection of text search parsers in a database"

    cls = TSParser
    query = \
        """SELECT nspname AS schema, prsname AS name,
                  prsstart::regproc AS start, prstoken::regproc AS gettoken,
                  prsend::regproc AS end, prslextype::regproc AS lextypes,
                  prsheadline::regproc AS headline,
                  obj_description(p.oid, 'pg_ts_parser') AS description
           FROM pg_ts_parser p
                JOIN pg_namespace n ON (prsnamespace = n.oid)
           WHERE (nspname != 'pg_catalog' AND nspname != 'information_schema')
           ORDER BY nspname, prsname"""

    def from_map(self, schema, inparsers):
        """Initialize the dictionary of parsers by examining the input map

        :param schema: schema owning the parsers
        :param inparsers: input YAML map defining the parsers
        """
        for key in inparsers.keys():
            if not key.startswith('text search parser '):
                raise KeyError("Unrecognized object type: %s" % key)
            tsp = key[19:]
            self[(schema.name, tsp)] = parser = TSParser(
                schema=schema.name, name=tsp)
            inparser = inparsers[key]
            if inparser:
                for attr, val in inparser.items():
                    setattr(parser, attr, val)
                if 'oldname' in inparser:
                    parser.oldname = inparser['oldname']
                    del inparser['oldname']
                if 'description' in inparser:
                    parser.description = inparser['description']

    def diff_map(self, inparsers):
        """Generate SQL to transform existing parsers

        :param input_map: a YAML map defining the new parsers
        :return: list of SQL statements

        Compares the existing parser definitions, as fetched from the
        catalogs, to the input map and generates SQL statements to
        transform the parsers accordingly.
        """
        stmts = []
        # check input parsers
        for (sch, tsp) in inparsers.keys():
            intsp = inparsers[(sch, tsp)]
            # does it exist in the database?
            if (sch, tsp) in self:
                stmts.append(self[(sch, tsp)].diff_map(intsp))
            else:
                # check for possible RENAME
                if hasattr(intsp, 'oldname'):
                    oldname = intsp.oldname
                    try:
                        stmts.append(self[oldname].rename(intsp.name))
                        del self[oldname]
                    except KeyError as exc:
                        exc.args = ("Previous name '%s' for parser '%s' "
                                   "not found" % (oldname, intsp.name), )
                        raise
                else:
                    # create new parser
                    stmts.append(intsp.create())
        # check database parsers
        for (sch, tsp) in self.keys():
            # if missing, drop it
            if (sch, tsp) not in inparsers:
                stmts.append(self[(sch, tsp)].drop())
        return stmts


class TSTemplate(DbSchemaObject):
    """A text search template definition"""

    keylist = ['schema', 'name']
    objtype = "TEXT SEARCH TEMPLATE"

    def create(self):
        """Return SQL statements to CREATE the template

        :return: SQL statements
        """
        clauses = []
        if hasattr(self, 'init'):
            clauses.append("INIT = %s" % self.init)
        clauses.append("LEXIZE = %s" % self.lexize)
        stmts = ["CREATE TEXT SEARCH TEMPLATE %s (\n    %s)" % (
                self.qualname(), ',\n    '.join(clauses))]
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts


class TSTemplateDict(DbObjectDict):
    "The collection of text search templates in a database"

    cls = TSTemplate
    query = \
        """SELECT nspname AS schema, tmplname AS name,
                  tmplinit::regproc AS init, tmpllexize::regproc AS lexize,
                  obj_description(p.oid, 'pg_ts_template') AS description
           FROM pg_ts_template p
                JOIN pg_namespace n ON (tmplnamespace = n.oid)
           WHERE (nspname != 'pg_catalog' AND nspname != 'information_schema')
           ORDER BY nspname, tmplname"""

    def from_map(self, schema, intemplates):
        """Initialize the dictionary of templates by examining the input map

        :param schema: schema owning the templates
        :param intemplates: input YAML map defining the templates
        """
        for key in intemplates.keys():
            if not key.startswith('text search template '):
                raise KeyError("Unrecognized object type: %s" % key)
            tst = key[21:]
            self[(schema.name, tst)] = template = TSTemplate(
                schema=schema.name, name=tst)
            intemplate = intemplates[key]
            if intemplate:
                for attr, val in intemplate.items():
                    setattr(template, attr, val)
                if 'oldname' in intemplate:
                    template.oldname = intemplate['oldname']
                    del intemplate['oldname']
                if 'description' in intemplate:
                    template.description = intemplate['description']

    def diff_map(self, intemplates):
        """Generate SQL to transform existing templates

        :param input_map: a YAML map defining the new templates
        :return: list of SQL statements

        Compares the existing template definitions, as fetched from the
        catalogs, to the input map and generates SQL statements to
        transform the templates accordingly.
        """
        stmts = []
        # check input templates
        for (sch, tst) in intemplates.keys():
            intst = intemplates[(sch, tst)]
            # does it exist in the database?
            if (sch, tst) in self:
                stmts.append(self[(sch, tst)].diff_map(intst))
            else:
                # check for possible RENAME
                if hasattr(intst, 'oldname'):
                    oldname = intst.oldname
                    try:
                        stmts.append(self[oldname].rename(intst.name))
                        del self[oldname]
                    except KeyError as exc:
                        exc.args = ("Previous name '%s' for template '%s' "
                                   "not found" % (oldname, intst.name), )
                        raise
                else:
                    # create new template
                    stmts.append(intst.create())
        # check database templates
        for (sch, tst) in self.keys():
            # if missing, drop it
            if (sch, tst) not in intemplates:
                stmts.append(self[(sch, tst)].drop())
        return stmts
