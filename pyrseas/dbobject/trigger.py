# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.trigger
    ~~~~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: Trigger derived from
    DbSchemaObject, and TriggerDict derived from DbObjectDict.
"""
from pyrseas.dbobject import DbObjectDict, DbSchemaObject
from pyrseas.dbobject import quote_id, commentable, split_schema_obj

EXEC_PROC = 'EXECUTE PROCEDURE '
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
            if arguments and '\\000' in arguments:
                args = ["'%s'" % a for a in arguments.split('\\000')[:-1]]
                self.procedure = "%s(%s)" % (procedure[:-2], ", ".join(args))
            else:
                self.procedure = procedure
        elif procedure[-1:] == ')':
            assert '(' in procedure, "No left parentheses in '%s'" % procedure
            self.procedure = procedure
        else:
            self.procedure = procedure + "()"
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
    def query():
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
            ORDER BY schema, "table", name"""

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
    def create(self):
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
        return ["CREATE %sTRIGGER %s\n    %s %s ON %s%s\n    FOR EACH %s"
                "%s\n    EXECUTE PROCEDURE %s" % (
                    constr, quote_id(self.name), self.timing.upper(), evts,
                    self._table.qualname(), defer,
                    self.level.upper(), cond, self.procedure)]

    def diff_map(self, intrg):
        """Generate SQL to transform an existing trigger

        :param intrigger: a YAML map defining the new trigger
        :return: list of SQL statements

        Compares the trigger to an input trigger and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []
        attrs = ['constraint', 'deferrable', 'initially_deferred',
                 'update', 'condition', 'procedure', 'timing', 'level']

        same = True
        for attr in attrs:
            if getattr(self, attr, None) != getattr(intrg, attr, None):
                same = False
                setattr(self, attr, getattr(intrg, attr, None))

        if set(self.events) != set(intrg.events):
            same = False
            self.events = intrg.events

        if not same:
            stmts.append("DROP TRIGGER %s" % self.identifier())
            stmts.append(self.create())

        stmts.append(self.diff_privileges(intrg))
        stmts.append(self.diff_description(intrg))

        return stmts

    def get_implied_deps(self, db):
        deps = super(Trigger, self).get_implied_deps(db)

        deps.add(db.tables[self.schema, self.table])

        # short-circuit augment triggers
        if hasattr(self, '_iscfg'):
            return deps

        # the trigger procedure can have arguments, but the trigger definition
        # has always none (they are accessed through `tg_argv`).
        # TODO: this breaks if a function name contains a '('
        # (another case for a robust lookup function in db)
        fschema, fname = split_schema_obj(self.procedure, self.schema)
        fname, _ = fname.split('(', 1)  # implicitly assert there is a (
        if not fname.startswith('tsvector_update_trigger'):
            deps.add(db.functions[fschema, fname, ''])

        return deps


class TriggerDict(DbObjectDict):
    "The collection of triggers in a database"
    cls = Trigger

    def from_map(self, table, intriggers):
        """Initalize the dictionary of triggers by converting the input map

        :param table: table owning the triggers
        :param intriggers: YAML map defining the triggers
        """
        for trg in intriggers:
            inobj = intriggers[trg]
            if not inobj:
                raise ValueError("Trigger '%s' has no specification" % trg)
            self[(table.schema, table.name, trg)] = trig = Trigger(
                trg, table.schema, table.name, inobj.pop('description', None),
                inobj.pop('procedure', None), inobj.pop('timing', None),
                inobj.pop('level', 'statement'), inobj.pop('events', []),
                inobj.pop('constraint', False),
                inobj.pop('deferrable', False),
                inobj.pop('initially_deferred', False),
                inobj.pop('columns', []), inobj.pop('condition', None))
            if 'oldname' in inobj:
                trig.oldname = inobj.get('oldname')
