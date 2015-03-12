# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.rule
    ~~~~~~~~~~~~~~~~~~~~~

    This defines two classes, Rule and RuleDict, derived from
    DbSchemaObject and DbObjectDict, respectively.
"""
from pyrseas.dbobject import DbObjectDict, DbSchemaObject
from pyrseas.dbobject import quote_id, commentable, split_schema_obj


class Rule(DbSchemaObject):
    """A rewrite rule definition"""

    keylist = ['schema', 'table', 'name']
    catalog_table = 'pg_rewrite'

    def identifier(self):
        """Return a full identifier for a rule object

        :return: string
        """
        return "%s ON %s" % (quote_id(self.name), self._table.qualname())

    def to_map(self, db):
        """Convert rule to a YAML-suitable format

        :return: dictionary
        """
        dct = self._base_map(db)
        return {self.name: dct}

    @commentable
    def create(self):
        """Return SQL statements to CREATE the rule

        :return: SQL statements
        """
        where = instead = ''
        if hasattr(self, 'condition'):
            where = ' WHERE %s' % self.condition
        if hasattr(self, 'instead'):
            instead = 'INSTEAD '
        return ["CREATE RULE %s AS ON %s\n    TO %s%s\n    DO %s%s" % (
                quote_id(self.name), self.event.upper(),
                self._table.qualname(), where, instead, self.actions)]

    def get_implied_deps(self, db):
        deps = super(Rule, self).get_implied_deps(db)
        deps.add(db.tables[split_schema_obj(self.table, self.schema)])
        return deps


class RuleDict(DbObjectDict):
    "The collection of rewrite rules in a database."

    cls = Rule
    query = \
        """SELECT r.oid,
                  nspname AS schema, relname AS table, rulename AS name,
                  split_part('select,update,insert,delete', ',',
                      ev_type::int - 48) AS event, is_instead AS instead,
                  pg_get_ruledef(r.oid) AS definition,
                  obj_description(r.oid, 'pg_rewrite') AS description
           FROM pg_rewrite r JOIN pg_class c ON (ev_class = c.oid)
                JOIN pg_namespace n ON (relnamespace = n.oid)
           WHERE relkind = 'r'
             AND (nspname != 'pg_catalog' AND nspname != 'information_schema')
           ORDER BY nspname, relname, rulename"""

    def _from_catalog(self):
        """Initialize the dictionary of rules by querying the catalogs"""
        for rule in self.fetch():
            do_loc = rule.definition.index(' DO ')
            if 'WHERE' in rule.definition:
                rule.condition = rule.definition[rule.definition.index(
                    ' WHERE ') + 7:do_loc]
            if hasattr(rule, 'instead') and rule.instead:
                do_loc += 8
            rule.actions = rule.definition[do_loc + 4:-1]
            del rule.definition
            self.by_oid[rule.oid] = self[rule.key()] = rule

    def from_map(self, table, inmap):
        """Initialize the dictionary of rules by examining the input map

        :param inmap: the input YAML map defining the rules
        """
        for rul in inmap:
            inrule = inmap[rul]
            rule = Rule(table=table.name, schema=table.schema, name=rul,
                        **inrule)
            if inrule:
                if 'oldname' in inrule:
                    rule.oldname = inrule['oldname']
                    del inrule['oldname']
                if 'description' in inrule:
                    rule.description = inrule['description']
            self[(table.schema, table.name, rul)] = rule
