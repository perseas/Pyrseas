# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.rule
    ~~~~~~~~~~~~~~~~~~~~~

    This defines two classes, Rule and RuleDict, derived from
    DbSchemaObject and DbObjectDict, respectively.
"""
from . import DbObjectDict, DbSchemaObject
from . import quote_id, commentable, split_schema_obj


class Rule(DbSchemaObject):
    """A rewrite rule definition"""

    keylist = ['schema', 'table', 'name']
    catalog = 'pg_rewrite'

    def __init__(self, name, schema, table, description, event, instead=False,
                 actions=None, condition=None, definition=None,
                 oid=None):
        """Initialize the rewrite rule

        :param name: rule name (from rulename)
        :param schema: schema name (from nspname via relnamespace/ev_class)
        :param table: table name (from relname via ev_class)
        :param description: comment text (from obj_description())
        :param event: event type (from ev_type)
        :param instead: is it an INSTEAD rule? (from is_instead)
        :param actions: rule actions (from ev_action via definition)
        :param condition: qualifying condition (from ev_qual via definition)
        :param definition: "raw" definition (from pg_get_ruledef)
        """
        super(Rule, self).__init__(name, schema, description)
        self._init_own_privs(None, [])
        self.table = table
        self.description = description
        self.event = event
        self.instead = instead
        if definition is not None:
            assert actions is None
            assert condition is None
            do_loc = definition.index(' DO ')
            if 'WHERE' in definition:
                self.condition = definition[
                    definition.index(' WHERE ') + 7:do_loc]
            if instead:
                do_loc += 8
            self.actions = definition[do_loc + 4:-1]
        else:
            self.actions = actions
            self.condition = condition
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        """Returns query to fetch Rule instances from the catalogs"""
        return """
            SELECT nspname AS schema, relname AS table, rulename AS name,
                   split_part('select,update,insert,delete', ',',
                       ev_type::int - 48) AS event, is_instead AS instead,
                   pg_get_ruledef(r.oid) AS definition,
                   obj_description(r.oid, 'pg_rewrite') AS description, r.oid
            FROM pg_rewrite r JOIN pg_class c ON (ev_class = c.oid)
                 JOIN pg_namespace n ON (relnamespace = n.oid)
            WHERE relkind = 'r'
              AND (nspname != 'pg_catalog' AND nspname != 'information_schema')
            ORDER BY nspname, relname, rulename"""

    @staticmethod
    def from_map(name, table, inobj):
        """Initialize a Rule instance from a YAML map

        :param name: rule name
        :param table: map of the table associated with the rule
        :param inobj: YAML map of the rule
        :return: Rule instance
        """
        obj = Rule(
            name, table.schema, table.name, inobj.pop('description', None),
            inobj.get('event'), inobj.pop('instead', False),
            inobj.pop('actions', None), inobj.pop('condition', None))
        obj.set_oldname(inobj)
        return obj

    def identifier(self):
        """Return a full identifier for a rule object

        :return: string
        """
        return "%s ON %s" % (quote_id(self.name), self._table.qualname())

    def to_map(self, db):
        """Convert rule to a YAML-suitable format

        :return: dictionary
        """
        dct = super(Rule, self).to_map(db)
        if not self.instead:
            dct.pop('instead')
        return {self.name: dct}

    @commentable
    def create(self, dbversion=None):
        """Return SQL statements to CREATE the rule

        :return: SQL statements
        """
        where = instead = ''
        if self.condition is not None:
            where = ' WHERE %s' % self.condition
        if self.instead:
            instead = 'INSTEAD '
        return ["CREATE RULE %s AS ON %s\n    TO %s%s\n    DO %s%s" % (
                quote_id(self.name), self.event.upper(),
                self._table.qualname(), where, instead, self.actions)]

    def get_implied_deps(self, db):
        """Return set of implicit dependencies

        :param db: Database.Dicts object
        :return: set of dependencies
        """
        deps = super(Rule, self).get_implied_deps(db)
        deps.add(db.tables[split_schema_obj(self.table, self.schema)])
        return deps


class RuleDict(DbObjectDict):
    "The collection of rewrite rules in a database."

    cls = Rule

    def from_map(self, table, inmap):
        """Initialize the dictionary of rules by examining the input map

        :param table: the input YAML map of the associated table
        :param inmap: the input YAML map defining the rules
        """
        for rul in inmap:
            inobj = inmap[rul]
            self[(table.schema, table.name, rul)] = Rule.from_map(
                rul, table, inobj)
