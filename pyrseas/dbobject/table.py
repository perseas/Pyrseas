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
from constraint import CheckConstraint, PrimaryKey, ForeignKey, \
    UniqueConstraint

MAX_BIGINT = 9223372036854775807L


class DbClass(DbSchemaObject):
    """A table, sequence or view"""

    keylist = ['schema', 'name']


class Sequence(DbClass):
    "A sequence generator definition"

    keylist = ['schema', 'name']
    objtype = "SEQUENCE"

    def get_attrs(self, dbconn):
        """Get the attributes for the sequence

        :param dbconn: a DbConnection object
        """
        data = dbconn.fetchone(
            """SELECT start_value, increment_by, max_value, min_value,
                      cache_value
               FROM %s.%s""" % (self.schema, self.name))
        for key, val in data.items():
            setattr(self, key, val)

    def get_owner(self, dbconn):
        """Get the table and column name that owns the sequence

        :param dbconn: a DbConnection object
        """
        data = dbconn.fetchone(
            """SELECT refobjid::regclass, refobjsubid
               FROM pg_depend
               WHERE objid = '%s'::regclass
                 AND refclassid = 'pg_class'::regclass""" % self.qualname())
        if data:
            self.owner_table = tbl = data[0]
            self.owner_column = data[1]
            if '.' in tbl:
                dot = tbl.index('.')
                if self.schema == tbl[:dot]:
                    self.owner_table = tbl[dot + 1:]

    def to_map(self):
        """Convert a sequence definition to a YAML-suitable format

        :return: dictionary
        """
        seq = {}
        for key, val in self.__dict__.items():
            if key in self.keylist:
                continue
            if key == 'max_value' and val == MAX_BIGINT:
                seq[key] = None
            elif key == 'min_value' and val == 1:
                seq[key] = None
            elif val <= sys.maxint:
                seq[key] = int(val)
            else:
                seq[key] = str(val)
        return {self.extern_key(): seq}

    def create(self):
        """Return a SQL statement to CREATE the sequence

        :return: SQL statement
        """
        maxval = self.max_value and ("MAXVALUE %d" % self.max_value) \
            or "NO MAXVALUE"
        minval = self.min_value and ("MINVALUE %d" % self.min_value) \
            or "NO MINVALUE"
        return """CREATE SEQUENCE %s
    START WITH %d
    INCREMENT BY %d
    %s
    %s
    CACHE %d""" % (self.qualname(), self.start_value, self.increment_by,
                   maxval, minval, self.cache_value)

    def add_owner(self):
        """Return statement to ALTER the sequence to indicate its owner table

        :return: SQL statement
        """
        stmts = []
        pth = self.set_search_path()
        if pth:
            stmts.append(pth)
        stmts.append("ALTER SEQUENCE %s OWNED BY %s.%s" % (
                self.name, self.owner_table, self.owner_column))
        return stmts

    def diff_map(self, inseq):
        """Generate SQL to transform an existing sequence

        :param inseq: a YAML map defining the new sequence
        :return: list of SQL statements

        Compares the sequence to an input sequence and generates SQL
        statements to transform it into the one represented by the
        input.
        """
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
            return "ALTER SEQUENCE %s" % self.qualname() + stmt
        return []


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
            cols.append(self.columns[i].to_map())
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
                tbl['indexes'].update(self.indexes[k.name].to_map(
                        self.column_names()))

        return {self.extern_key(): tbl}

    def create(self):
        """Return a SQL statement to CREATE the table

        :return: SQL statement
        """
        cols = []
        for col in self.columns:
            cols.append("    " + col.add())
        return "CREATE TABLE %s (\n%s)" % (self.qualname(), ",\n".join(cols))

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
        dbcols = len(self.columns)

        base = "ALTER TABLE %s\n    " % self.qualname()
        # check input columns
        for (num, incol) in enumerate(intable.columns):
            # add new columns
            if num >= dbcols:
                stmts.append(base + "ADD COLUMN %s" % incol.add())
            # check existing columns
            # TODO: more work is needed, for columns out of order
            elif self.columns[num].name == incol.name:
                stmt = self.columns[num].diff_map(incol)
                if stmt:
                    stmts.append(base + stmt)

        return stmts


class ClassDict(DbObjectDict):
    "The collection of tables and similar objects in a database"

    cls = DbClass
    query = \
        """SELECT nspname AS schema, relname AS name, relkind AS kind
           FROM pg_class
                JOIN pg_namespace ON (relnamespace = pg_namespace.oid)
                JOIN pg_roles ON (nspowner = pg_roles.oid)
           WHERE relkind in ('r', 'S')
                 AND (nspname = 'public' OR rolname <> 'postgres')
           ORDER BY nspname, relname"""

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
                inst.get_owner(self.dbconn)

    def from_map(self, schema, inobjs, newdb):
        """Initalize the dictionary of tables by converting the input map

        :param schema: schema owning the tables
        :param inobjs: YAML map defining the schema objects
        :param newdb: collection of dictionaries defining the database
        """
        for k in inobjs.keys():
            spc = k.find(' ')
            if spc == -1:
                raise KeyError("Unrecognized object type: %s" % k)
            objtype = k[:spc]
            key = k[spc + 1:]
            if objtype == 'table':
                self[(schema.name, key)] = table = Table(
                    schema=schema.name, name=key)
                intable = inobjs[k]
                if not intable:
                    raise ValueError("Table '%s' has no specification" % k)
                try:
                    newdb.columns.from_map(table, intable['columns'])
                except KeyError, exc:
                    exc.args = ("Table '%s' has no columns" % key, )
                    raise
                if 'oldname' in intable:
                    table.oldname = intable['oldname']
                newdb.constraints.from_map(table, intable)
                if 'indexes' in intable:
                    newdb.indexes.from_map(table, intable['indexes'])
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
            else:
                raise KeyError("Unrecognized object type: %s" % k)

    def link_refs(self, dbcolumns, dbconstrs, dbindexes):
        """Connect columns, constraints, etc. to their respective tables

        :param dbcolumns: dictionary of columns
        :param dbconstrs: dictionary of constraints
        :param dbindexes: dictionary of indexes

        Links each list of table columns in `dbcolumns` to the
        corresponding table. Fills the `foreign_keys`,
        `unique_constraints` and `indexes` dictionaries for each table
        by traversing the `dbconstrs` and `dbindexes` dictionaries,
        which are keyed by schema, table and constraint or index.
        """
        for (sch, tbl) in dbcolumns.keys():
            assert self[(sch, tbl)]
            self[(sch, tbl)].columns = dbcolumns[(sch, tbl)]
        for (sch, tbl) in self.keys():
            if isinstance(self[(sch, tbl)], Sequence):
                seq = self[(sch, tbl)]
                if hasattr(seq, 'owner_table'):
                    if isinstance(seq.owner_column, int):
                        seq.owner_column = self[(sch, seq.owner_table)]. \
                            column_names()[seq.owner_column - 1]
        for (sch, tbl, cns) in dbconstrs.keys():
            constr = dbconstrs[(sch, tbl, cns)]
            if (sch, tbl) not in self:  # check constraints on domains
                continue
            table = self[(sch, tbl)]
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

    def _rename(self, obj, objtype):
        """Process a RENAME"""
        stmt = ''
        oldname = obj.oldname
        try:
            stmt = self[(obj.schema, oldname)].rename(obj.name)
            del self[(obj.schema, oldname)]
        except KeyError, exc:
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
        for (sch, tbl) in intables.keys():
            intable = intables[(sch, tbl)]
            if not isinstance(intable, Table):
                continue
            # does it exist in the database?
            if (sch, tbl) not in self:
                if hasattr(intable, 'oldname'):
                    stmts.append(self._rename(intable, "table"))
                else:
                    # create new table
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

        # check database tables and sequences
        for (sch, tbl) in self.keys():
            table = self[(sch, tbl)]
            # if missing, mark it for dropping
            if (sch, tbl) not in intables:
                table.dropped = False
            else:
                # check table/sequence objects
                stmts.append(table.diff_map(intables[(sch, tbl)]))

        # now drop the marked tables
        for (sch, tbl) in self.keys():
            table = self[(sch, tbl)]
            if isinstance(table, Sequence) and hasattr(table, 'owner_table'):
                continue
            if hasattr(table, 'dropped') and not table.dropped:
                # drop subordinate objects first
                if hasattr(table, 'check_constraints'):
                    for chk in table.check_constraints:
                        stmts.append(table.check_constraints[chk].drop())
                if hasattr(table, 'unique_constraints'):
                    for unq in table.unique_constraints:
                        stmts.append(table.unique_constraints[unq].drop())
                if hasattr(table, 'indexes'):
                    for idx in table.indexes:
                        stmts.append(table.indexes[idx].drop())
                if hasattr(table, 'foreign_keys'):
                    for fgn in table.foreign_keys:
                        stmts.append(table.foreign_keys[fgn].drop())
                if hasattr(table, 'primary_key'):
                    # TODO there can be more than one referred_by
                    if hasattr(table, 'referred_by'):
                        stmts.append(table.referred_by.drop())
                    stmts.append(table.primary_key.drop())
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
