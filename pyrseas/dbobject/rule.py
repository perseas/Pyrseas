# -*- coding: utf-8 -*-
"""
    pyrseas.rule
    ~~~~~~~~~~~~

    This defines two classes, Rule and RuleDict, derived from
    DbSchemaObject and DbObjectDict, respectively.
"""
from pyrseas.dbobject import DbObjectDict, DbSchemaObject, quote_id


class Rule(DbSchemaObject):
    """A rewrite rule definition"""

    keylist = ['schema', 'table', 'name']
    objtype = "RULE"

    def identifier(self):
        """Return a full identifier for a rule object

        :return: string
        """
        return "%s ON %s" % (quote_id(self.name), self._table.qualname())

    def to_map(self):
        """Convert rule to a YAML-suitable format

        :return: dictionary
        """
        dct = self._base_map()
        del dct['_table']
        return {self.name: dct}

    def create(self):
        """Return SQL statements to CREATE the rule

        :return: SQL statements
        """
        stmts = []
        where = instead = ''
        if hasattr(self, 'condition'):
            where = ' WHERE %s' % self.condition
        if hasattr(self, 'instead'):
            instead = 'INSTEAD '
        stmts.append("CREATE RULE %s AS ON %s\n    TO %s%s\n    DO %s%s" % (
                quote_id(self.name), self.event.upper(),
                self._table.qualname(), where, instead, self.actions))
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts


class RuleDict(DbObjectDict):
    "The collection of rewrite rules in a database."

    cls = Rule
    query = \
        """SELECT nspname AS schema, relname AS table, rulename AS name,
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
            self[rule.key()] = rule

    def from_map(self, table, inmap):
        """Initialize the dictionary of rules by examining the input map

        :param inmap: the input YAML map defining the rules
        """
        for rul in inmap.keys():
            inrule = inmap[rul]
            rule = Rule(table=table.name, schema=table.schema,
                                    name=rul, **inrule)
            if inrule:
                if 'oldname' in inrule:
                    rule.oldname = inrule['oldname']
                    del inrule['oldname']
                if 'description' in inrule:
                    rule.description = inrule['description']
            self[(table.schema, table.name, rul)] = rule

    def diff_map(self, inrules):
        """Generate SQL to transform existing rules

        :param input_map: a YAML map defining the new rules
        :return: list of SQL statements

        Compares the existing rule definitions, as fetched from the
        catalogs, to the input map and generates SQL statements to
        transform the rules accordingly.
        """
        stmts = []
        # check input rules
        for rul in inrules.keys():
            inrul = inrules[rul]
            # does it exist in the database?
            if rul in self:
                stmts.append(self[rul].diff_map(inrul))
            else:
                # check for possible RENAME
                if hasattr(inrul, 'oldname'):
                    oldname = inrul.oldname
                    try:
                        stmts.append(self[oldname].rename(inrul.name))
                        del self[oldname]
                    except KeyError as exc:
                        exc.args = ("Previous name '%s' for rule '%s' "
                                    "not found" % (oldname, inrul.name), )
                        raise
                else:
                    # create new rule
                    stmts.append(inrul.create())
        # check database rules
        for (sch, tbl, rul) in self.keys():
            # if missing, drop it
            if (sch, tbl, rul) not in inrules:
                stmts.append(self[(sch, tbl, rul)].drop())

        return stmts
