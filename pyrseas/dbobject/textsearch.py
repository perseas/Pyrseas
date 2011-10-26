# -*- coding: utf-8 -*-
"""
    pyrseas.textsearch
    ~~~~~~~~~~~~~~~~~~

    This defines classes, TSParser and TSParserDict, derived from
    DbObject and DbObjectDict, respectively.
"""
from pyrseas.dbobject import DbObjectDict, DbSchemaObject, quote_id


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
                quote_id(self.name), ',\n    '.join(clauses))]
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
                    except KeyError, exc:
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
