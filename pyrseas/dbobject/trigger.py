# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.trigger
    ~~~~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: Trigger derived from
    DbSchemaObject, and TriggerDict derived from DbObjectDict.
"""
from . import DbObjectDict, DbSchemaObject
from . import quote_id, commentable, split_schema_obj
from .function import split_schema_func, join_schema_func

EVENT_TYPES = ['insert', 'delete', 'update', 'truncate']


class Trigger(DbSchemaObject):
    """A procedural language trigger"""

    keylist = ['schema', 'table', 'name']
    catalog = 'pg_trigger'

    def __init__(self, name, schema, table, description, procedure, timing,
                 level, events, constraint=False, deferrable=False,
                 initially_deferred=False,
                 columns=[], condition=None, arguments='',
                 oid=None):
        """Initialize the trigger

        :param name: trigger name (from tgname)
        :param schema: schema name (from tgnamespace)
        :param table: table name (from relname via tgrelid)
        :param description: comment text (from obj_description())
        :param procedure: function to call (from tgfoid)
        :param level: row/statement (from tgtype bit 0)
        :param timing: before/after/instead of (from tgtype bit 1 and 6)
        :param events: insert/update/delete/truncate (from tgtype bits 2-5)
        :param constraint: is it a constraint trigger? (from contype)
        :param deferrable: is it deferrable? (from tgdeferrrable)
        :param initially_deferred: initially deferred? (from tginitdeferred)
        :param columns: array of column numbers (from tgattr)
        :param condition: WHEN condition
        :param arguments: arguments to pass to trigger (from tgargs)
        """
        super(Trigger, self).__init__(name, schema, description)
        self._init_own_privs(None, [])
        self.table = table
        if procedure[-2:] == '()':
            procedure = procedure[:-2]
        if '.' in procedure:
            self.procedure = split_schema_obj(procedure, self.schema)
        else:
            self.procedure = procedure
        if arguments and '\\000' in arguments:
            self.arguments = ", ".join(["'%s'" % a for a in
                                        arguments.split('\\000')[:-1]])
        else:
            self.arguments = arguments if len(arguments) > 0 else None
        # see Postgres include/catalog/pg_trigger.h
        if isinstance(timing, int):
            if timing == (1 << 1):
                self.timing = 'before'
            elif timing == (1 << 6):
                self.timing = 'instead of'
            else:
                self.timing = 'after'
        else:
            self.timing = timing
        self.level = level
        if isinstance(events, int):
            self.events = []
            for (n, ev) in enumerate(EVENT_TYPES):
                if events & 1 << n:
                    self.events.append(ev)
        else:
            assert isinstance(events, list), "Events must be a list"
            self.events = events
        self.constraint = constraint
        self.deferrable = deferrable
        self.initially_deferred = initially_deferred
        self.columns = columns
        self.condition = condition
        if condition is not None and condition.startswith('CREATE '):
            if 'WHEN (' in condition:
                self.condition = condition[condition.index("WHEN (")+6:
                                           condition.index(") EXECUTE ")]
            else:
                self.condition = None
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT nspname AS schema, relname AS table, tgname AS name,
                   tgfoid::regprocedure AS procedure,
                   CASE WHEN tgtype::integer::bit = '1' THEN 'row'
                        ELSE 'statement' END AS level,
                   (tgtype::integer::bit(7) & B'1000010')::integer AS timing,
                   (tgtype >> 2)::integer::bit(4)::integer AS events,
                   CASE WHEN contype = 't' THEN true ELSE false END AS
                        constraint,
                   tgdeferrable AS deferrable,
                   tginitdeferred AS initially_deferred, tgattr AS columns,
                   encode(tgargs, 'escape') AS arguments,
                   pg_get_triggerdef(t.oid) AS condition,
                   obj_description(t.oid, 'pg_trigger') AS description, t.oid
            FROM pg_trigger t JOIN pg_class c ON (t.tgrelid = c.oid)
                 JOIN pg_namespace n ON (c.relnamespace = n.oid)
                 JOIN pg_roles ON (n.nspowner = pg_roles.oid)
                 LEFT JOIN pg_constraint cn ON (tgconstraint = cn.oid)
            WHERE NOT tgisinternal
              AND (nspname != 'pg_catalog' AND nspname != 'information_schema')
              AND t.tgfoid NOT IN (
                  SELECT objid FROM pg_depend WHERE deptype = 'e'
                               AND classid = 'pg_proc'::regclass)
            ORDER BY schema, "table", name"""

    @staticmethod
    def from_map(name, table, inobj):
        """Initialize a trigger instance from a YAML map

        :param name: trigger name
        :param table: table map
        :param inobj: YAML map of the trigger
        :return: trigger instance
        """
        proc = inobj.pop("procedure")
        args = ""
        if isinstance(proc, str):
            if proc[-2:] == "()":
                proc = proc[:-2]
            elif proc[-1:] == ')':
                proc, args = proc[:-1].split('(')
        else:  # should be a dict
            args = proc.pop("arguments", None)
            proc = proc.pop("name")
        obj = Trigger(
            name, table.schema, table.name, inobj.pop('description', None),
            proc, inobj.pop('timing', None), inobj.pop('level', 'statement'),
            inobj.pop('events', []), inobj.pop('constraint', False),
            inobj.pop('deferrable', False),
            inobj.pop('initially_deferred', False), inobj.pop('columns', []),
            inobj.pop('condition', None), args)
        obj.set_oldname(inobj)
        return obj

    def identifier(self):
        """Returns a full identifier for the trigger

        :return: string
        """
        return "%s ON %s" % (quote_id(self.name), self._table.qualname())

    def to_map(self, db):
        """Convert a trigger to a YAML-suitable format

        :return: dictionary
        """
        dct = super(Trigger, self).to_map(db)
        schfunc = join_schema_func(self.procedure)
        if self.arguments is not None:
            dct["procedure"] = {"name": schfunc, "arguments": self.arguments}
        else:
            dct["procedure"] = schfunc
        dct.pop("arguments")
        for attr in ['constraint', 'deferrable', 'initially_deferred']:
            if dct[attr] is False:
                del dct[attr]
        if len(self.columns) > 0:
            dct['columns'] = [self._table.column_names()[int(k) - 1]
                              for k in self.columns.split()]
        else:
            del dct['columns']
        if self.condition is None:
            del dct['condition']
        return {self.name: dct}

    @commentable
    def create(self, dbversion=None):
        """Return SQL statements to CREATE the trigger

        :return: SQL statements
        """
        constr = defer = ''
        if self.constraint:
            constr = "CONSTRAINT "
            if self.deferrable:
                defer = "DEFERRABLE "
            if self.initially_deferred:
                defer += "INITIALLY DEFERRED"
            if defer:
                defer = '\n    ' + defer
        evts = " OR ".join(self.events).upper()
        if len(self.columns) > 0 and 'update' in self.events:
            evts = evts.replace("UPDATE", "UPDATE OF %s" % (
                ", ".join(self.columns)))
        cond = ''
        if self.condition is not None:
            cond = "\n    WHEN (%s)" % self.condition
        if isinstance(self.procedure, tuple):
            procname = "%s.%s" % self.procedure
        else:
            procname = self.procedure
        if self.arguments is None:
            args = ""
        else:
            args = self.arguments
        return ["CREATE %sTRIGGER %s\n    %s %s ON %s%s\n    FOR EACH %s"
                "%s\n    EXECUTE PROCEDURE %s(%s)" % (
                    constr, quote_id(self.name), self.timing.upper(), evts,
                    self._table.qualname(), defer,
                    self.level.upper(), cond, procname, args)]

    def alter(self, inobj):
        """Generate SQL to transform an existing trigger

        :param inobj: a YAML map defining the new trigger
        :return: list of SQL statements
        """
        stmts = []
        if self.procedure != inobj.procedure or \
           self.arguments != inobj.arguments or self.events != inobj.events \
           or self.level != inobj.level or self.timing != inobj.timing:
            stmts.append(self.drop())
            stmts.append(inobj.create())
        stmts.append(self.diff_description(inobj))
        return stmts

    def get_implied_deps(self, db):
        deps = super(Trigger, self).get_implied_deps(db)

        deps.add(db.tables[self.schema, self.table])

        # short-circuit augment triggers
        if hasattr(self, '_iscfg'):
            return deps

        # the trigger procedure can have arguments, but the trigger definition
        # has always none (they are accessed through `tg_argv`).
        if isinstance(self.procedure, tuple):
            fschema, fname = self.procedure
            deps.add(db.functions[fschema, fname, ''])

        return deps


class TriggerDict(DbObjectDict):
    "The collection of triggers in a database"
    cls = Trigger

    def from_map(self, table, intriggers):
        """Initialize the dictionary of triggers by converting the input map

        :param table: table owning the triggers
        :param intriggers: YAML map defining the triggers
        """
        for trg in intriggers:
            inobj = intriggers[trg]
            self[(table.schema, table.name, trg)] = Trigger.from_map(
                trg, table, inobj)
