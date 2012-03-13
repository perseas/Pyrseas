# -*- coding: utf-8 -*-
"""
    pyrseas.table
    ~~~~~~~~~~~~~

    This module defines four classes: DbClass derived from
    DbSchemaObject, Sequence and Table derived from DbClass, and
    ClassDict derived from DbObjectDict.
"""
import sys

from pyrseas.dbobject import DbObjectDict, DbSchemaObject
from pyrseas.dbobject import quote_id, split_schema_obj
from pyrseas.dbobject.constraint import CheckConstraint, PrimaryKey
from pyrseas.dbobject.constraint import ForeignKey, UniqueConstraint

MAX_BIGINT = 9223372036854775807


class DbClass(DbSchemaObject):
    """A table, sequence or view"""

    keylist = ['schema', 'name']


class Sequence(DbClass):
    "A sequence generator definition"

    objtype = "SEQUENCE"

    def get_attrs(self, dbconn):
        """Get the attributes for the sequence

        :param dbconn: a DbConnection object
        """
        data = dbconn.fetchone(
            """SELECT start_value, increment_by, max_value, min_value,
                      cache_value
               FROM %s.%s""" % (quote_id(self.schema), quote_id(self.name)))
        for key, val in data.items():
            setattr(self, key, val)

    def get_dependent_table(self, dbconn):
        """Get the table and column name that uses or owns the sequence

        :param dbconn: a DbConnection object
        """
        data = dbconn.fetchone(
            """SELECT refobjid::regclass, refobjsubid
               FROM pg_depend
               WHERE objid = '%s'::regclass
                 AND refclassid = 'pg_class'::regclass""" % self.qualname())
        if data:
            (sch, self.owner_table) = split_schema_obj(data[0], self.schema)
            self.owner_column = data[1]
            return
        data = dbconn.fetchone(
            """SELECT adrelid::regclass
               FROM pg_attrdef a JOIN pg_depend ON (a.oid = objid)
               WHERE refobjid = '%s'::regclass
               AND classid = 'pg_attrdef'::regclass""" % self.qualname())
        if data:
            (sch, self.dependent_table) = split_schema_obj(
                data[0], self.schema)

    def to_map(self):
        """Convert a sequence definition to a YAML-suitable format

        :return: dictionary
        """
        seq = {}
        for key, val in self.__dict__.items():
            if key in self.keylist or key == 'dependent_table':
                continue
            if key == 'max_value' and val == MAX_BIGINT:
                seq[key] = None
            elif key == 'min_value' and val == 1:
                seq[key] = None
            else:
                if sys.version < '3':
                    if isinstance(val, (int, long)) and val <= sys.maxsize:
                        seq[key] = val
                    else:
                        seq[key] = str(val)
                else:
                    if isinstance(val, int):
                        seq[key] = int(val)
                    else:
                        seq[key] = str(val)
        return {self.extern_key(): seq}

    def create(self):
        """Return a SQL statement to CREATE the sequence

        :return: SQL statements
        """
        stmts = []
        maxval = self.max_value and ("MAXVALUE %d" % self.max_value) \
            or "NO MAXVALUE"
        minval = self.min_value and ("MINVALUE %d" % self.min_value) \
            or "NO MINVALUE"
        stmts.append("""CREATE SEQUENCE %s
    START WITH %d
    INCREMENT BY %d
    %s
    %s
    CACHE %d""" % (self.qualname(), self.start_value, self.increment_by,
                   maxval, minval, self.cache_value))
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts

    def add_owner(self):
        """Return statement to ALTER the sequence to indicate its owner table

        :return: SQL statement
        """
        stmts = []
        pth = self.set_search_path()
        if pth:
            stmts.append(pth)
        stmts.append("ALTER SEQUENCE %s OWNED BY %s.%s" % (
                quote_id(self.name), quote_id(self.owner_table),
                quote_id(self.owner_column)))
        return stmts

    def diff_map(self, inseq):
        """Generate SQL to transform an existing sequence

        :param inseq: a YAML map defining the new sequence
        :return: list of SQL statements

        Compares the sequence to an input sequence and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []
        stmt = ""
        if self.start_value != inseq.start_value:
            stmt += " START WITH %d" % inseq.start_value
        if self.increment_by != inseq.increment_by:
            stmt += " INCREMENT BY %d" % inseq.increment_by
        maxval = self.max_value
        if maxval == MAX_BIGINT:
            maxval = None
        if maxval != inseq.max_value:
            stmt += inseq.max_value and (" MAXVALUE %d" % inseq.max_value) \
                or " NO MAXVALUE"
        minval = self.min_value
        if minval == 1:
            minval = None
        if minval != inseq.min_value:
            stmt += inseq.min_value and (" MINVALUE %d" % inseq.min_value) \
                or " NO MINVALUE"
        if self.cache_value != inseq.cache_value:
            stmt += " CACHE %d" % inseq.cache_value
        if stmt:
            stmts.append("ALTER SEQUENCE %s" % self.qualname() + stmt)
        stmts.append(self.diff_description(inseq))
        return stmts


class Table(DbClass):
    """A database table definition

    A table is identified by its schema name and table name.  It should
    have a list of columns.  It may have a primary_key, zero or more
    foreign_keys, zero or more unique_constraints, and zero or more
    indexes.
    """

    objtype = "TABLE"

    def column_names(self):
        """Return a list of column names in the table

        :return: list
        """
        return [c.name for c in self.columns]

    def to_map(self, dbschemas):
        """Convert a table to a YAML-suitable format

        :param dbschemas: database dictionary of schemas
        :return: dictionary
        """
        if not hasattr(self, 'columns'):
            return
        cols = []
        for i in range(len(self.columns)):
            col = self.columns[i].to_map()
            if col:
                cols.append(col)
        tbl = {'columns': cols}
        if hasattr(self, 'description'):
            tbl.update(description=self.description)
        if hasattr(self, 'check_constraints'):
            if not 'check_constraints' in tbl:
                tbl.update(check_constraints={})
            for k in self.check_constraints.values():
                tbl['check_constraints'].update(
                    self.check_constraints[k.name].to_map(self.column_names()))
        if hasattr(self, 'primary_key'):
            tbl.update(primary_key=self.primary_key.to_map(
                    self.column_names()))
        if hasattr(self, 'foreign_keys'):
            if not 'foreign_keys' in tbl:
                tbl['foreign_keys'] = {}
            for k in self.foreign_keys.values():
                tbls = dbschemas[k.ref_schema].tables
                tbl['foreign_keys'].update(self.foreign_keys[k.name].to_map(
                        self.column_names(),
                        tbls[self.foreign_keys[k.name].ref_table]. \
                            column_names()))
        if hasattr(self, 'unique_constraints'):
            if not 'unique_constraints' in tbl:
                tbl.update(unique_constraints={})
            for k in self.unique_constraints.values():
                tbl['unique_constraints'].update(
                    self.unique_constraints[k.name].to_map(
                        self.column_names()))
        if hasattr(self, 'indexes'):
            if not 'indexes' in tbl:
                tbl['indexes'] = {}
            for k in self.indexes.values():
                tbl['indexes'].update(self.indexes[k.name].to_map())
        if hasattr(self, 'inherits'):
            if not 'inherits' in tbl:
                tbl['inherits'] = self.inherits
        if hasattr(self, 'rules'):
            if not 'rules' in tbl:
                tbl['rules'] = {}
            for k in self.rules.values():
                tbl['rules'].update(self.rules[k.name].to_map())
        if hasattr(self, 'triggers'):
            if not 'triggers' in tbl:
                tbl['triggers'] = {}
            for k in self.triggers.values():
                tbl['triggers'].update(self.triggers[k.name].to_map())

        return {self.extern_key(): tbl}

    def create(self):
        """Return SQL statements to CREATE the table

        :return: SQL statements
        """
        stmts = []
        if hasattr(self, 'created'):
            return stmts
        cols = []
        for col in self.columns:
            if not (hasattr(col, 'inherited') and col.inherited):
                cols.append("    " + col.add()[0])
        inhclause = ''
        if hasattr(self, 'inherits'):
            inhclause = " INHERITS (%s)" % ", ".join(t for t in self.inherits)
        stmts.append("CREATE TABLE %s (\n%s)%s" % (
                self.qualname(), ",\n".join(cols), inhclause))
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        for col in self.columns:
            if hasattr(col, 'description'):
                stmts.append(col.comment())
        self.created = True
        return stmts

    def drop(self):
        """Return a SQL DROP statement for the table

        :return: SQL statement
        """
        stmts = []
        if not hasattr(self, 'dropped') or not self.dropped:
            if hasattr(self, 'dependent_funcs'):
                for fnc in self.dependent_funcs:
                    stmts.append(fnc.drop())
            self.dropped = True
            stmts.append("DROP TABLE %s" % self.identifier())
        return stmts

    def diff_map(self, intable):
        """Generate SQL to transform an existing table

        :param intable: a YAML map defining the new table
        :return: list of SQL statements

        Compares the table to an input table and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []
        if not hasattr(intable, 'columns'):
            raise KeyError("Table '%s' has no columns" % intable.name)
        colnames = [col.name for col in self.columns
                    if not hasattr(col, 'dropped')]
        dbcols = len(colnames)

        base = "ALTER %s %s\n    " % (self.objtype, self.qualname())
        # check input columns
        for (num, incol) in enumerate(intable.columns):
            if hasattr(incol, 'oldname'):
                assert(self.columns[num].name == incol.oldname)
                stmts.append(self.columns[num].rename(incol.name))
            # add new columns
            if num >= dbcols:
                (stmt, descr) = incol.add()
                stmts.append(base + "ADD COLUMN %s" % stmt)
                if descr:
                    stmts.append(descr)
            # check existing columns
            elif self.columns[num].name == incol.name:
                (stmt, descr) = self.columns[num].diff_map(incol)
                if stmt:
                    stmts.append(base + stmt)
                if descr:
                    stmts.append(descr)
            elif incol.name not in colnames:
                (stmt, descr) = incol.add()
                stmts.append(base + "ADD COLUMN %s" % stmt)
                if descr:
                    stmts.append(descr)

        stmts.append(self.diff_description(intable))

        return stmts


class View(DbClass):
    """A database view definition

    A view is identified by its schema name and view name.
    """

    objtype = "VIEW"

    def create(self, newdefn=None):
        """Return SQL statements to CREATE the table

        :return: SQL statements
        """
        stmts = []
        defn = newdefn or self.definition
        if defn[-1:] == ';':
            defn = defn[:-1]
        stmts.append("CREATE%s VIEW %s AS\n   %s" % (
                newdefn and " OR REPLACE" or '', self.qualname(), defn))
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts

    def diff_map(self, inview):
        """Generate SQL to transform an existing view

        :param inview: a YAML map defining the new view
        :return: list of SQL statements

        Compares the view to an input view and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []
        if self.definition != inview.definition:
            stmts.append(self.create(inview.definition))
        stmts.append(self.diff_description(inview))
        return stmts


class ClassDict(DbObjectDict):
    "The collection of tables and similar objects in a database"

    cls = DbClass
    query = \
        """SELECT nspname AS schema, relname AS name, relkind AS kind,
                  CASE WHEN relkind = 'v' THEN pg_get_viewdef(c.oid, TRUE)
                       ELSE '' END AS definition,
                  obj_description(c.oid, 'pg_class') AS description
           FROM pg_class c
                JOIN pg_namespace ON (relnamespace = pg_namespace.oid)
           WHERE relkind in ('r', 'S', 'v')
                 AND (nspname != 'pg_catalog'
                      AND nspname != 'information_schema')
           ORDER BY nspname, relname"""

    inhquery = \
        """SELECT inhrelid::regclass AS sub, inhparent::regclass AS parent,
                  inhseqno
           FROM pg_inherits
           ORDER BY 1, 3"""

    def _from_catalog(self):
        """Initialize the dictionary of tables by querying the catalogs"""
        for table in self.fetch():
            sch, tbl = table.key()
            kind = table.kind
            del table.kind
            if kind == 'r':
                self[(sch, tbl)] = Table(**table.__dict__)
            elif kind == 'S':
                self[(sch, tbl)] = inst = Sequence(**table.__dict__)
                inst.get_attrs(self.dbconn)
                inst.get_dependent_table(self.dbconn)
            elif kind == 'v':
                self[(sch, tbl)] = View(**table.__dict__)
        for (tbl, partbl, num) in self.dbconn.fetchall(self.inhquery):
            (sch, tbl) = split_schema_obj(tbl)
            table = self[(sch, tbl)]
            if not hasattr(table, 'inherits'):
                table.inherits = []
            table.inherits.append(partbl)

    def from_map(self, schema, inobjs, newdb):
        """Initalize the dictionary of tables by converting the input map

        :param schema: schema owning the tables
        :param inobjs: YAML map defining the schema objects
        :param newdb: collection of dictionaries defining the database
        """
        for k in inobjs.keys():
            (objtype, spc, key) = k.partition(' ')
            if spc != ' ' or objtype not in ['table', 'sequence', 'view']:
                raise KeyError("Unrecognized object type: %s" % k)
            if objtype == 'table':
                self[(schema.name, key)] = table = Table(
                    schema=schema.name, name=key)
                intable = inobjs[k]
                if not intable:
                    raise ValueError("Table '%s' has no specification" % k)
                try:
                    newdb.columns.from_map(table, intable['columns'])
                except KeyError as exc:
                    exc.args = ("Table '%s' has no columns" % key, )
                    raise
                if 'inherits' in intable:
                    table.inherits = intable['inherits']
                if 'oldname' in intable:
                    table.oldname = intable['oldname']
                newdb.constraints.from_map(table, intable)
                if 'indexes' in intable:
                    newdb.indexes.from_map(table, intable['indexes'])
                if 'rules' in intable:
                    newdb.rules.from_map(table, intable['rules'])
                if 'triggers' in intable:
                    newdb.triggers.from_map(table, intable['triggers'])
                if 'description' in intable:
                    table.description = intable['description']
            elif objtype == 'sequence':
                self[(schema.name, key)] = seq = Sequence(
                    schema=schema.name, name=key)
                inseq = inobjs[k]
                if not inseq:
                    raise ValueError("Sequence '%s' has no specification" % k)
                for attr, val in inseq.items():
                    setattr(seq, attr, val)
                if 'oldname' in inseq:
                    seq.oldname = inseq['oldname']
            elif objtype == 'view':
                self[(schema.name, key)] = view = View(
                    schema=schema.name, name=key)
                inview = inobjs[k]
                if not inview:
                    raise ValueError("View '%s' has no specification" % k)
                for attr, val in inview.items():
                    setattr(view, attr, val)
                if 'oldname' in inview:
                    view.oldname = inview['oldname']
            else:
                raise KeyError("Unrecognized object type: %s" % k)

    def link_refs(self, dbcolumns, dbconstrs, dbindexes, dbrules, dbtriggers):
        """Connect columns, constraints, etc. to their respective tables

        :param dbcolumns: dictionary of columns
        :param dbconstrs: dictionary of constraints
        :param dbindexes: dictionary of indexes
        :param dbrules: dictionary of rules
        :param dbtriggers: dictionary of triggers

        Links each list of table columns in `dbcolumns` to the
        corresponding table. Fills the `foreign_keys`,
        `unique_constraints`, `indexes` and `triggers` dictionaries
        for each table by traversing the `dbconstrs`, `dbindexes` and
        `dbtriggers` dictionaries, which are keyed by schema, table
        and constraint, index or trigger name.
        """
        for (sch, tbl) in dbcolumns.keys():
            if (sch, tbl) in self:
                assert isinstance(self[(sch, tbl)], Table)
                self[(sch, tbl)].columns = dbcolumns[(sch, tbl)]
                for col in dbcolumns[(sch, tbl)]:
                    col._table = self[(sch, tbl)]
        for (sch, tbl) in self.keys():
            table = self[(sch, tbl)]
            if isinstance(table, Sequence) and hasattr(table, 'owner_table'):
                if isinstance(table.owner_column, int):
                    table.owner_column = self[(sch, table.owner_table)]. \
                        column_names()[table.owner_column - 1]
            elif isinstance(table, Table) and hasattr(table, 'inherits'):
                for partbl in table.inherits:
                    (parsch, partbl) = split_schema_obj(partbl)
                    assert self[(parsch, partbl)]
                    parent = self[(parsch, partbl)]
                    if not hasattr(parent, 'descendants'):
                        parent.descendants = []
                    parent.descendants.append(table)
        for (sch, tbl, cns) in dbconstrs.keys():
            constr = dbconstrs[(sch, tbl, cns)]
            if hasattr(constr, 'target'):
                continue
            assert self[(sch, tbl)]
            constr._table = table = self[(sch, tbl)]
            if isinstance(constr, CheckConstraint):
                if not hasattr(table, 'check_constraints'):
                    table.check_constraints = {}
                table.check_constraints.update({cns: constr})
            elif isinstance(constr, PrimaryKey):
                table.primary_key = constr
            elif isinstance(constr, ForeignKey):
                if not hasattr(table, 'foreign_keys'):
                    table.foreign_keys = {}
                # link referenced and referrer
                constr.references = self[(constr.ref_schema, constr.ref_table)]
                # TODO: there can be more than one
                self[(constr.ref_schema, constr.ref_table)].referred_by = \
                    constr
                table.foreign_keys.update({cns: constr})
            elif isinstance(constr, UniqueConstraint):
                if not hasattr(table, 'unique_constraints'):
                    table.unique_constraints = {}
                table.unique_constraints.update({cns: constr})
        for (sch, tbl, idx) in dbindexes.keys():
            assert self[(sch, tbl)]
            table = self[(sch, tbl)]
            if not hasattr(table, 'indexes'):
                table.indexes = {}
            table.indexes.update({idx: dbindexes[(sch, tbl, idx)]})
        for (sch, tbl, rul) in dbrules.keys():
            assert self[(sch, tbl)]
            table = self[(sch, tbl)]
            if not hasattr(table, 'rules'):
                table.rules = {}
            table.rules.update({rul: dbrules[(sch, tbl, rul)]})
            dbrules[(sch, tbl, rul)]._table = self[(sch, tbl)]
        for (sch, tbl, trg) in dbtriggers.keys():
            assert self[(sch, tbl)]
            table = self[(sch, tbl)]
            if not hasattr(table, 'triggers'):
                table.triggers = {}
            table.triggers.update({trg: dbtriggers[(sch, tbl, trg)]})
            dbtriggers[(sch, tbl, trg)]._table = self[(sch, tbl)]

    def _rename(self, obj, objtype):
        """Process a RENAME"""
        stmt = ''
        oldname = obj.oldname
        try:
            stmt = self[(obj.schema, oldname)].rename(obj.name)
            self[(obj.schema, obj.name)] = self[(obj.schema, oldname)]
            del self[(obj.schema, oldname)]
        except KeyError as exc:
            exc.args = ("Previous name '%s' for %s '%s' not found" % (
                    oldname, objtype, obj.name), )
            raise
        return stmt

    def diff_map(self, intables):
        """Generate SQL to transform existing tables and sequences

        :param intables: a YAML map defining the new tables/sequences
        :return: list of SQL statements

        Compares the existing table/sequence definitions, as fetched
        from the catalogs, to the input map and generates SQL
        statements to transform the tables/sequences accordingly.
        """
        stmts = []
        # first pass: sequences owned by a table
        for (sch, seq) in intables.keys():
            inseq = intables[(sch, seq)]
            if not isinstance(inseq, Sequence) or \
                    not hasattr(inseq, 'owner_table'):
                continue
            if (sch, seq) not in self:
                if hasattr(inseq, 'oldname'):
                    stmts.append(self._rename(inseq, "sequence"))
                else:
                    # create new sequence
                    stmts.append(inseq.create())

        # check input tables
        inhstack = []
        for (sch, tbl) in intables.keys():
            intable = intables[(sch, tbl)]
            if not isinstance(intable, Table):
                continue
            # does it exist in the database?
            if (sch, tbl) not in self:
                if not hasattr(intable, 'oldname'):
                    # create new table
                    if hasattr(intable, 'inherits'):
                        inhstack.append(intable)
                    else:
                        stmts.append(intable.create())
                else:
                    stmts.append(self._rename(intable, "table"))
        while len(inhstack):
            intable = inhstack.pop()
            createit = True
            for partbl in intable.inherits:
                if intables[split_schema_obj(partbl)] in inhstack:
                    createit = False
            if createit:
                stmts.append(intable.create())
            else:
                inhstack.insert(0, intable)

        # check input views
        for (sch, tbl) in intables.keys():
            intable = intables[(sch, tbl)]
            if not isinstance(intable, View):
                continue
            # does it exist in the database?
            if (sch, tbl) not in self:
                if hasattr(intable, 'oldname'):
                    stmts.append(self._rename(intable, "view"))
                else:
                    # create new view
                    stmts.append(intable.create())

        # second pass: input sequences not owned by tables
        for (sch, seq) in intables.keys():
            inseq = intables[(sch, seq)]
            if not isinstance(inseq, Sequence):
                continue
            # does it exist in the database?
            if (sch, seq) not in self:
                if hasattr(inseq, 'oldname'):
                    stmts.append(self._rename(inseq, "sequence"))
                elif hasattr(inseq, 'owner_table'):
                    stmts.append(inseq.add_owner())
                else:
                    # create new sequence
                    stmts.append(inseq.create())

        # check database tables, sequences and views
        for (sch, tbl) in self.keys():
            table = self[(sch, tbl)]
            # if missing, mark it for dropping
            if (sch, tbl) not in intables:
                table.dropped = False
            else:
                # check table/sequence/view objects
                stmts.append(table.diff_map(intables[(sch, tbl)]))

        # now drop the marked tables
        for (sch, tbl) in self.keys():
            table = self[(sch, tbl)]
            if isinstance(table, Sequence) and hasattr(table, 'owner_table'):
                continue
            if hasattr(table, 'dropped') and not table.dropped:
                # first, drop all foreign keys
                if hasattr(table, 'foreign_keys'):
                    for fgn in table.foreign_keys:
                        stmts.append(table.foreign_keys[fgn].drop())
                # and drop the triggers
                if hasattr(table, 'triggers'):
                    for trg in table.triggers:
                        stmts.append(table.triggers[trg].drop())
                if hasattr(table, 'rules'):
                    for rul in table.rules:
                        stmts.append(table.rules[rul].drop())
                # drop views
                if isinstance(table, View):
                    stmts.append(table.drop())

        inhstack = []
        for (sch, tbl) in self.keys():
            table = self[(sch, tbl)]
            if (isinstance(table, Sequence) \
                    and (hasattr(table, 'owner_table') \
                             or hasattr(table, 'dependent_table'))) \
                             or isinstance(table, View):
                continue
            if hasattr(table, 'dropped') and not table.dropped:
                # next, drop other subordinate objects
                if hasattr(table, 'check_constraints'):
                    for chk in table.check_constraints:
                        stmts.append(table.check_constraints[chk].drop())
                if hasattr(table, 'unique_constraints'):
                    for unq in table.unique_constraints:
                        stmts.append(table.unique_constraints[unq].drop())
                if hasattr(table, 'indexes'):
                    for idx in table.indexes:
                        stmts.append(table.indexes[idx].drop())
                if hasattr(table, 'rules'):
                    for rul in table.rules:
                        stmts.append(table.rules[rul].drop())
                if hasattr(table, 'primary_key'):
                    # TODO there can be more than one referred_by
                    if hasattr(table, 'referred_by'):
                        stmts.append(table.referred_by.drop())
                    stmts.append(table.primary_key.drop())
                # finally, drop the table itself
                if hasattr(table, 'descendants'):
                    inhstack.append(table)
                else:
                    stmts.append(table.drop())
        while len(inhstack):
            table = inhstack.pop()
            dropit = True
            for childtbl in table.descendants:
                if self[(childtbl.schema, childtbl.name)] in inhstack:
                    dropit = False
            if dropit:
                stmts.append(table.drop())
            else:
                inhstack.insert(0, table)
        for (sch, tbl) in self.keys():
            table = self[(sch, tbl)]
            if isinstance(table, Sequence) \
                    and hasattr(table, 'dependent_table') \
                    and hasattr(table, 'dropped') and not table.dropped:
                stmts.append(table.drop())

        # last pass to deal with nextval DEFAULTs
        for (sch, tbl) in intables.keys():
            intable = intables[(sch, tbl)]
            if not isinstance(intable, Table):
                continue
            if (sch, tbl) not in self:
                for col in intable.columns:
                    if hasattr(col, 'default') \
                            and col.default.startswith('nextval'):
                        stmts.append(col.set_sequence_default())

        return stmts
