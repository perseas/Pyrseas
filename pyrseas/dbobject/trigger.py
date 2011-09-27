# -*- coding: utf-8 -*-
"""
    pyrseas.trigger
    ~~~~~~~~~~~~~~~

    This module defines two classes: Trigger derived from
    DbSchemaObject, and TriggerDict derived from DbObjectDict.
"""
from pyrseas.dbobject import DbObjectDict, DbSchemaObject, quote_id


EXEC_PROC = 'EXECUTE PROCEDURE '
EVENT_TYPES = ['INSERT', 'UPDATE', 'DELETE', 'TRUNCATE']


class Trigger(DbSchemaObject):
    """A procedural language trigger"""

    keylist = ['schema', 'table', 'name']
    objtype = "TRIGGER"

    def identifier(self):
        """Returns a full identifier for the trigger

        :return: string
        """
        return "%s ON %s" % (quote_id(self.name), self._table.qualname())

    def to_map(self):
        """Convert a trigger to a YAML-suitable format

        :return: dictionary
        """
        dct = self._base_map()
        del dct['_table']
        if hasattr(self, 'columns'):
            dct['columns'] = [self._table.column_names()[int(k) - 1]
                              for k in self.columns.split()]
        return {self.name: dct}

    def create(self):
        """Return SQL statements to CREATE the trigger

        :return: SQL statements
        """
        stmts = []
        constr = defer = ''
        if hasattr(self, 'constraint') and self.constraint:
            constr = "CONSTRAINT "
            if hasattr(self, 'deferrable') and self.deferrable:
                defer = "DEFERRABLE "
            if hasattr(self, 'initially_deferred') and self.initially_deferred:
                defer += "INITIALLY DEFERRED"
            if defer:
                defer = '\n    ' + defer
        evts = " OR ".join(self.events).upper()
        if hasattr(self, 'columns') and 'update' in self.events:
            evts = evts.replace("UPDATE", "UPDATE OF %s" % (
                    ", ".join(self.columns)))
        cond = ''
        if hasattr(self, 'condition'):
            cond = "\n    WHEN (%s)" % self.condition
        stmts.append("CREATE %sTRIGGER %s\n    %s %s ON %s%s\n    FOR EACH %s"
                     "%s\n    EXECUTE PROCEDURE %s" % (
                constr, quote_id(self.name), self.timing.upper(), evts,
                self._table.qualname(), defer,
                self.level.upper(), cond, self.procedure))
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts


QUERY_PRE90 = \
        """SELECT nspname AS schema, relname AS table,
                  tgname AS name, tgisconstraint AS constraint,
                  tgdeferrable AS deferrable,
                  tginitdeferred AS initially_deferred,
                  pg_get_triggerdef(t.oid) AS definition,
                  NULL AS columns,
                  obj_description(t.oid, 'pg_trigger') AS description
           FROM pg_trigger t
                JOIN pg_class c ON (t.tgrelid = c.oid)
                JOIN pg_namespace n ON (c.relnamespace = n.oid)
                JOIN pg_roles ON (n.nspowner = pg_roles.oid)
                LEFT JOIN pg_constraint cn ON (tgconstraint = cn.oid)
           WHERE contype != 'f' OR contype IS NULL
             AND (nspname != 'pg_catalog' AND nspname != 'information_schema')
           ORDER BY 1, 2, 3"""


class TriggerDict(DbObjectDict):
    "The collection of triggers in a database"

    cls = Trigger
    query = \
        """SELECT nspname AS schema, relname AS table,
                  tgname AS name, pg_get_triggerdef(t.oid) AS definition,
                  CASE WHEN contype = 't' THEN true ELSE false END AS
                       constraint,
                  tgdeferrable AS deferrable,
                  tginitdeferred AS initially_deferred,
                  tgattr AS columns,
                  obj_description(t.oid, 'pg_trigger') AS description
           FROM pg_trigger t
                JOIN pg_class c ON (t.tgrelid = c.oid)
                JOIN pg_namespace n ON (c.relnamespace = n.oid)
                JOIN pg_roles ON (n.nspowner = pg_roles.oid)
                LEFT JOIN pg_constraint cn ON (tgconstraint = cn.oid)
           WHERE NOT tgisinternal
             AND (nspname != 'pg_catalog' AND nspname != 'information_schema')
           ORDER BY 1, 2, 3"""

    def _from_catalog(self):
        """Initialize the dictionary of triggers by querying the catalogs"""
        if self.dbconn.version < 90000:
            self.query = QUERY_PRE90
        for trig in self.fetch():
            if 'BEFORE ' in trig.definition:
                trig.timing = 'before'
                evtstart = trig.definition.index('BEFORE ') + 7
            else:
                trig.timing = 'after'
                evtstart = trig.definition.index('AFTER ') + 6
            evtend = trig.definition.index(' ON ', evtstart)
            events = trig.definition[evtstart:evtend]
            trig.events = []
            for evt in EVENT_TYPES:
                if evt in events:
                    trig.events.append(evt.lower())
            trig.level = ('FOR EACH ROW' in trig.definition and 'row' or
                          'statement')
            if 'WHEN (' in trig.definition:
                trig.condition = trig.definition[
                    trig.definition.index('WHEN (') + 6:
                        trig.definition.index(') EXECUTE PROCEDURE')]
            trig.procedure = trig.definition[trig.definition.index(EXEC_PROC)
                                             + len(EXEC_PROC):]
            del trig.definition
            self[trig.key()] = trig

    def from_map(self, table, intriggers):
        """Initalize the dictionary of triggers by converting the input map

        :param table: table owning the triggers
        :param intriggers: YAML map defining the triggers
        """
        for trg in intriggers.keys():
            intrig = intriggers[trg]
            if not intrig:
                raise ValueError("Trigger '%s' has no specification" % trg)
            self[(table.schema, table.name, trg)] = trig = Trigger(
                schema=table.schema, table=table.name, name=trg)
            for attr, val in intrig.items():
                setattr(trig, attr, val)
            if not hasattr(trig, 'level'):
                trig.level = 'statement'
            if 'oldname' in intrig:
                trig.oldname = intrig['oldname']
            if 'description' in intrig:
                trig.description = intrig['description']

    def diff_map(self, intriggers):
        """Generate SQL to transform existing triggers

        :param intriggers: a YAML map defining the new triggers
        :return: list of SQL statements

        Compares the existing trigger definitions, as fetched from
        the catalogs, to the input map and generates SQL statements to
        transform the triggers accordingly.
        """
        stmts = []
        # check input triggers
        for (sch, tbl, trg) in intriggers.keys():
            intrig = intriggers[(sch, tbl, trg)]
            # does it exist in the database?
            if (sch, tbl, trg) not in self:
                if not hasattr(intrig, 'oldname'):
                    # create new trigger
                    stmts.append(intrig.create())
                else:
                    stmts.append(self[(sch, tbl, trg)].rename(intrig))
            else:
                # check trigger objects
                stmts.append(self[(sch, tbl, trg)].diff_map(intrig))

        # check existing triggers
        for (sch, tbl, trg) in self.keys():
            trig = self[(sch, tbl, trg)]
            # if missing, drop them
            if (sch, tbl, trg) not in intriggers:
                    stmts.append(trig.drop())

        return stmts
