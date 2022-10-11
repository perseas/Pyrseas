# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.table
    ~~~~~~~~~~~~~~~~~~~~~~

    This module defines four classes: DbClass derived from
    DbSchemaObject, Sequence and Table derived from DbClass, and
    ClassDict derived from DbObjectDict.
"""

import re
import os
import sys

from . import DbObjectDict, DbSchemaObject, split_schema_obj
from . import quote_id, commentable, ownable, grantable
from .constraint import CheckConstraint, PrimaryKey
from .constraint import ForeignKey, UniqueConstraint
from .privileges import add_grant

MAX_BIGINT = 9223372036854775807


def seq_max_value(seq):
    if seq.max_value is None or seq.max_value == MAX_BIGINT:
        return " NO MAXVALUE"
    return " MAXVALUE %d" % seq.max_value


def seq_min_value(seq):
    if seq.min_value is None or seq.min_value == 1:
        return " NO MINVALUE"
    return " MINVALUE %d" % seq.min_value


class DbClass(DbSchemaObject):
    """A table, sequence or view

    The `pg_class` catalog also includes Postgres indexes, but for now,
    indexes have not been implemented as part of the `DbClass` hierarchy.
    """

    keylist = ['schema', 'name']
    catalog = 'pg_class'

    def __init__(self, name, schema, description, owner, privileges):
        """Initialize the relation "class"

        :param name: relation name (from relname)
        :param schema: schema name (from relnamespace)
        :param description: comment text (from obj_description())
        :param owner: owner name (from rolname via relowner)
        :param privileges: access privileges (from relacl)
        """
        super(DbClass, self).__init__(name, schema, description)
        self._init_own_privs(owner, privileges)


class Sequence(DbClass):
    "A sequence generator definition"

    def __init__(self, name, schema, description, owner, privileges,
                 start_value=1, increment_by=1, max_value=MAX_BIGINT,
                 min_value=1, cache_value=1, data_type='bigint',
                 owner_table=None, owner_column=None,
                 oid=None):
        """Initialize the sequence

        :param name-privileges: see DbClass.__init__ params
        :param start_value: start value (from start_value)
        :param max_value: maximum value (from max_value)
        :param increment_by: value to add (from increment_by)
        :param min_value: minimum value (from min_value)
        :param cache_value: cache value (from cache_value/cache_size)
        :param data_type: data type (from data_type)
        :param owner_table: owner table
        :param owner_column: owner column
        """
        super(Sequence, self).__init__(name, schema, description, owner,
                                       privileges)
        self.start_value = start_value
        self.increment_by = increment_by
        self.max_value = max_value
        self.min_value = min_value
        self.cache_value = cache_value
        self.data_type = data_type
        self.owner_table = owner_table
        self.owner_column = owner_column
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT nspname AS schema, relname AS name, rolname AS owner,
                   array_to_string(relacl, ',') AS privileges,
                   obj_description(c.oid, 'pg_class') AS description, c.oid
            FROM pg_class c JOIN pg_roles r ON (r.oid = relowner)
                 JOIN pg_namespace ON (relnamespace = pg_namespace.oid)
            WHERE relkind = 'S'
              AND nspname != 'pg_catalog' AND nspname != 'information_schema'
              AND c.oid NOT IN (
                  SELECT objid FROM pg_depend WHERE deptype = 'e'
                  AND classid = 'pg_class'::regclass)
            ORDER BY nspname, relname"""

    @staticmethod
    def from_map(name, schema, inobj):
        """Initialize a sequence instance from a YAML map

        :param name: sequence name
        :param name: schema map
        :param inobj: YAML map of the sequence
        :return: sequence instance
        """
        obj = Sequence(
            name, schema.name, inobj.pop('description', None),
            inobj.pop('owner', None), inobj.pop('privileges', []),
            inobj.pop('start_value', 1), inobj.pop('increment_by', 1),
            inobj.pop('max_value', MAX_BIGINT), inobj.pop('min_value', 1),
            inobj.pop('cache_value', 1), inobj.pop('data_type', 'bigint'),
            inobj.pop('owner_table', None), inobj.pop('owner_column', None))
        obj.fix_privileges()
        obj.set_oldname(inobj)
        return obj

    @property
    def allprivs(self):
        return 'rwU'

    def get_attrs(self, dbconn):
        """Get the attributes for the sequence

        :param dbconn: a DbConnection object
        """
        query = """SELECT start_value, increment_by, max_value, min_value,
                          cache_size AS cache_value, data_type
                   FROM pg_sequences
                   WHERE schemaname = '%s'
                   AND sequencename = '%s'""" % (self.schema, self.name)
        data = dbconn.fetchone(query)

        for key, val in list(data.items()):
            setattr(self, key, val)

    def get_dependent_table(self, dbconn):
        """Get the table and column name that uses or owns the sequence

        :param dbconn: a DbConnection object
        """

        def split_table(obj, sch):
            schema = sch
            tbl = obj
            quoted = '"%s".' % schema
            if obj.startswith(schema + '.'):
                tbl = obj[len(schema) + 1:]
            elif obj.startswith(quoted):
                tbl = obj[len(quoted):]
            elif sch is None:
                raise ValueError("Invalid schema.table: %s" % obj)
            if tbl[0] == '"' and tbl[-1:] == '"':
                tbl = tbl[1:-1]
            return tbl

        data = dbconn.fetchone(
            """SELECT refobjid::regclass, refobjsubid
               FROM pg_depend
               WHERE objid = '%s'::regclass
                 AND refclassid = 'pg_class'::regclass""" % self.identifier())
        if data:
            self.owner_table = split_table(data["refobjid"], self.schema)
            self.owner_column = data["refobjsubid"]
            return
        data = dbconn.fetchone(
            """SELECT adrelid::regclass AS regclass
               FROM pg_attrdef a JOIN pg_depend ON (a.oid = objid)
               WHERE refobjid = '%s'::regclass
               AND classid = 'pg_attrdef'::regclass""" % self.qualname())
        if data:
            self.dependent_table = split_table(data["regclass"], self.schema)

    def to_map(self, db, opts):
        """Convert a sequence definition to a YAML-suitable format

        :param opts: options to include/exclude tables, etc.
        :return: dictionary
        """
        if hasattr(opts, 'tables') and opts.tables and \
                (self.name not in opts.tables and
                 self.owner_table is None or
                 self.owner_table not in opts.tables) or (
                     hasattr(opts, 'excl_tables') and opts.excl_tables and
                     self.name in opts.excl_tables):
            return None
        dct = super(Sequence, self).to_map(db, opts.no_owner, opts.no_privs)
        if self.owner_table is None and self.owner_column is None:
            dct.pop('owner_table')
            dct.pop('owner_column')
        dct.pop('dependent_table', None)
        if self.data_type == 'bigint':
            dct.pop('data_type')
        for key, val in list(dct.items()):
            if key == 'max_value' and val == MAX_BIGINT:
                dct[key] = None
            elif key == 'min_value' and val == 1:
                dct[key] = None
            elif key == 'privileges':
                dct[key] = val
            else:
                if isinstance(val, int):
                    dct[key] = int(val)
                else:
                    dct[key] = str(val)

        return dct

    def _common_create_spec(self):
        return """    START WITH %d
    INCREMENT BY %d
   %s
   %s
    CACHE %d""" % (self.start_value, self.increment_by, seq_min_value(self),
                   seq_max_value(self), self.cache_value)

    @commentable
    @grantable
    @ownable
    def create(self, dbversion=None):
        """Return a SQL statement to CREATE the sequence

        :return: SQL statements
        """
        mod = ""
        if self.data_type != 'bigint':
            mod = "\n    AS %s" % self.data_type
        if hasattr(self, '_owner_col'):
            if self._owner_col.identity is not None:
                return []
        return ["CREATE SEQUENCE %s%s%s" % (self.qualname(), mod,
                                            self._common_create_spec())]

    def add_inline(self):
        """Return statement to create the sequence inline as part of a
           GENERATED AS IDENTITY clause
        """
        return "SEQUENCE NAME %s%s" % (self.qualname(),
                                       self._common_create_spec())

    def add_owner(self):
        """Return statement to ALTER the sequence to indicate its owner table

        :return: SQL statement
        """
        stmts = []
        stmts.append("ALTER SEQUENCE %s OWNED BY %s.%s" % (
            self.qualname(), self.qualname(self.schema, self.owner_table),
            quote_id(self.owner_column)))
        return stmts

    def alter(self, inseq, no_owner=False):
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
        minval = self.min_value
        if minval == 1:
            minval = None
        if minval != inseq.min_value:
            stmt += seq_min_value(inseq)
        maxval = self.max_value
        if maxval == MAX_BIGINT:
            maxval = None
        if maxval != inseq.max_value:
            stmt += seq_max_value(inseq)
        if self.cache_value != inseq.cache_value:
            stmt += " CACHE %d" % inseq.cache_value
        if stmt:
            stmts.append("ALTER SEQUENCE %s" % self.qualname() + stmt)

        if inseq.owner_column is not None and inseq.owner_table is None:
            raise ValueError("Sequence '%s' incomplete specification: "
                             "owner_column but no owner_table")
        if inseq.owner_table is not None:
            if inseq.owner_column is None:
                raise ValueError("Sequence '%s' incomplete specification: "
                                 "owner_table but no owner_column")
            if self.owner_table is None and self.owner_column is None:
                stmts.append(inseq.add_owner())

        stmts.append(super(Sequence, self).alter(inseq, no_owner=no_owner))
        return stmts

    def drop(self):
        """Generate SQL to drop the current sequence

        :return: list of SQL statements
        """
        stmts = []
        if self.owner_table is None:
            stmts.append(super(Sequence, self).drop())
        return stmts


PARTITIONING_STRATEGIES = {'l': 'list', 'r': 'range'}


class Table(DbClass):
    """A database table definition

    A table is identified by its schema name and table name.  It should
    have a list of columns.  It may have a primary_key, zero or more
    foreign_keys, zero or more unique_constraints, and zero or more
    indexes.

    A :class:`Table` can also represent a partitioned table or a
    partition of a partitioned table.  The latter's columns are all
    inherited from the parent (partitioned) table, so they are not
    shown in an output map (or expected on input).
    """
    def __init__(self, name, schema, description, owner, privileges,
                 tablespace=None, unlogged=False, options=None,
                 partition_bound_spec=None, partition_by=None,
                 partition_cols=None, partition_exprs=None,
                 oid=None):
        """Initialize the table

        :param name-privileges: see DbClass.__init__ params
        :param tablespace: storage tablespace (from reltablespace)
        :param unlogged: unlogged indicator (from relpersistence = 'u')
        :param options: access method options (from reloptions)
        :param partition_bound_spec: partition bound (from relpartbound)
        :param partition_by: partitioning strategy (from partstrat)
        """
        super(Table, self).__init__(name, schema, description, owner,
                                    privileges)
        self.tablespace = tablespace
        self.unlogged = unlogged
        self.options = options
        if partition_bound_spec is None:
            self.partition_bound_spec = None
        elif partition_bound_spec.startswith("FOR VALUES "):
            self.partition_bound_spec = partition_bound_spec[11:]
        else:
            self.partition_bound_spec = partition_bound_spec
        if partition_by is None:
            self.partition_by = None
        elif isinstance(partition_by, dict):
            partby = list(partition_by.keys())[0]
            self.partition_by = partby
            self.partition_cols = partition_by[partby]
        elif len(partition_by) == 1:
            self.partition_by = PARTITIONING_STRATEGIES[partition_by]
        else:
            assert partition_by in PARTITIONING_STRATEGIES.values()
            self.partition_by = partition_by
        if partition_cols is not None and len(partition_cols) > 0:
            self.partition_cols = [int(n) for n in partition_cols.split(' ')]
        elif partition_cols is None and partition_by is None:
            self.partition_cols = partition_cols
        self.partition_exprs = partition_exprs
        self.columns = []
        self.inherits = []
        self.check_constraints = {}
        self.primary_key = None
        self.foreign_keys = {}
        self.unique_constraints = {}
        self.indexes = {}
        self.triggers = {}
        self.rules = {}
        self.oid = oid
        self._referred_by = []

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT nspname AS schema, relname AS name, reloptions AS options,
                   spcname AS tablespace, relpersistence = 'u' AS unlogged,
                   rolname AS owner,
                   array_to_string(relacl, ',') AS privileges,
                   pg_get_expr(relpartbound, c.oid) AS partition_bound_spec,
                   partstrat AS partition_by, partattrs AS partition_cols,
                   pg_get_expr(partexprs, pt.partrelid) AS partition_exprs,
                   obj_description(c.oid, 'pg_class') AS description, c.oid
            FROM pg_class c JOIN pg_roles r ON (r.oid = relowner)
                 JOIN pg_namespace ON (relnamespace = pg_namespace.oid)
                 LEFT JOIN pg_tablespace t ON (reltablespace = t.oid)
                 LEFT JOIN pg_partitioned_table pt ON c.oid = pt.partrelid
            WHERE relkind IN ('r', 'p') AND relpersistence != 't'
              AND nspname != 'pg_catalog' AND nspname != 'information_schema'
              AND c.oid NOT IN (
                  SELECT objid FROM pg_depend WHERE deptype = 'e'
                  AND classid = 'pg_class'::regclass)
            ORDER BY nspname, relname"""

    @staticmethod
    def inhquery():
        return """SELECT inhrelid::regclass AS sub,
                         inhparent::regclass AS parent, inhseqno
                  FROM pg_inherits
                  ORDER BY 1, 3"""

    @staticmethod
    def from_map(name, schema, inobj):
        """Initialize a table instance from a YAML map

        :param name: table name
        :param name: schema map
        :param inobj: YAML map of the table
        :return: table instance
        """
        obj = Table(
            name, schema.name, inobj.pop('description', None),
            inobj.pop('owner', None), inobj.pop('privileges', []),
            inobj.pop('tablespace', None), inobj.pop('unlogged', False),
            inobj.pop('options', None),
            inobj.pop('partition_bound_spec', None),
            inobj.pop('partition_by', None))
        if obj.partition_bound_spec is not None:
            obj.inherits = [inobj.get('partition_of')]
        obj.fix_privileges()
        obj.set_oldname(inobj)
        return obj

    @property
    def allprivs(self):
        return 'arwdDxt'

    def _normalize_partcols(self):
        "Replace integer column numbers by column names"
        if isinstance(self.partition_cols[0], int):
            self.partition_cols = [self.columns[k - 1].name
                                   for k in self.partition_cols]

    def column_names(self):
        """Return a list of column names in the table

        :return: list
        """
        return [c.name for c in self.columns]

    def to_map(self, db, dbschemas, opts):
        """Convert a table to a YAML-suitable format

        :param dbschemas: database dictionary of schemas
        :param opts: options to include/exclude tables, etc.
        :return: dictionary
        """
        if hasattr(opts, 'excl_tables') and opts.excl_tables \
                and self.name in opts.excl_tables or len(self.columns) == 0:
            return None

        dct = super(Table, self).to_map(db, opts.no_owner, opts.no_privs)

        for attr in ('tablespace', 'options', 'partition_bound_spec'):
            if dct[attr] is None:
                dct.pop(attr)
        if self.unlogged is False:
            dct.pop('unlogged')
        if len(self.inherits) == 0:
            dct.pop('inherits')

        if self.partition_bound_spec is None:
            cols = []
            for column in self.columns:
                col = column.to_map(db, opts.no_privs)
                if col:
                    cols.append(col)
            dct['columns'] = cols
        else:
            dct.pop('columns')
            assert len(self.inherits) == 1
            dct.update(partition_of=self.inherits[0])
            dct.pop('inherits')

        if self.partition_by is not None:
            assert self.partition_cols is not None
            self._normalize_partcols()
            dct.update(partition_by={self.partition_by: self.partition_cols})
        else:
            dct.pop('partition_by')
        dct.pop('partition_cols')
        dct.pop('partition_exprs')

        if len(self.check_constraints) > 0:
            for k in list(self.check_constraints.values()):
                dct['check_constraints'].update(
                    self.check_constraints[k.name].to_map(
                        db, self.column_names()))
        else:
            dct.pop('check_constraints')
        if self.primary_key is not None:
            dct['primary_key'] = self.primary_key.to_map(
                db, self.column_names())
        else:
            dct.pop('primary_key')
        if len(self.foreign_keys) > 0:
            for k in list(self.foreign_keys.values()):
                tbls = dbschemas[k.ref_schema].tables
                ktable = self.foreign_keys[k.name]
                dct['foreign_keys'].update(ktable.to_map(
                    db, self.column_names(),
                    tbls[ktable.ref_table].column_names()))
        else:
            dct.pop('foreign_keys')
        if len(self.unique_constraints) > 0:
            for k in list(self.unique_constraints.values()):
                dct['unique_constraints'].update(
                    self.unique_constraints[k.name].to_map(
                        db, self.column_names()))
        else:
            dct.pop('unique_constraints')
        if len(self.indexes) > 0:
            idxs = {}
            for idx in self.indexes.values():
                if not getattr(idx, '_for_constraint', None):
                    idxs.update(idx.to_map(db))
            if idxs:
                # we may have only indexes not to dump, e.g. the pkey one
                dct['indexes'] = idxs
            else:
                dct.pop('indexes', None)
        else:
            dct.pop('indexes')
        if len(self.rules) > 0:
            for k in list(self.rules.values()):
                dct['rules'].update(self.rules[k.name].to_map(db))
        else:
            dct.pop('rules')
        if len(self.triggers) > 0:
            for k in list(self.triggers.values()):
                dct['triggers'].update(self.triggers[k.name].to_map(db))
        else:
            dct.pop('triggers')

        return dct

    def create(self, dbversion=None):
        """Return SQL statements to CREATE the table

        :return: SQL statements
        """
        stmts = []
        cols = []
        colprivs = []
        for col in self.columns:
            if not col.inherited:
                cols.append("    " + col.add()[0])
            colprivs.append(col.add_privs())
        unlogged = 'UNLOGGED ' if self.unlogged else ''

        partbyclause = partofclause = inhclause = collist = ""
        if self.partition_by is not None:
            partbyclause = " PARTITION BY %s (%s)" % (
                self.partition_by.upper(), ", ".join(self.partition_cols))
        elif len(self.inherits) > 0:
            inhclause = " INHERITS (%s)" % ", ".join(
                self.qualname(self.schema, t) for t in self.inherits)
        if self.partition_bound_spec is None:
            collist = "(\n%s)" % ",\n".join(cols)
        else:
            partofclause = "PARTITION OF %s FOR VALUES %s" % (
                self.inherits[0], self.partition_bound_spec)
            inhclause = ""

        opts = ''
        if self.options is not None:
            opts = " WITH (%s)" % ', '.join(self.options)
        tblspc = ''
        if self.tablespace is not None:
            tblspc = " TABLESPACE %s" % self.tablespace
        stmts.append("CREATE %sTABLE %s %s%s%s%s%s%s" % (
            unlogged, self.qualname(), collist, partbyclause, partofclause,
            inhclause, opts, tblspc))
        if self.owner is not None:
            stmts.append(self.alter_owner())
        for priv in self.privileges:
            stmts.append(add_grant(self, priv))
        if colprivs:
            stmts.append(colprivs)
        if self.description is not None:
            stmts.append(self.comment())
        for col in self.columns:
            if col.description is not None:
                stmts.append(col.comment())
        if hasattr(self, '_owned_seqs'):
            for dep in self._owned_seqs:
                stmts.append(dep.add_owner())
        self.created = True
        return stmts

    def drop(self):
        """Return a SQL DROP statement for the table

        :return: SQL statement
        """
        stmts = []
        if not hasattr(self, 'dropped') or not self.dropped:
            if hasattr(self, '_dependent_funcs'):
                for fnc in self._dependent_funcs:
                    stmts.append(fnc.drop())
            self.dropped = True
            stmts.append("DROP TABLE %s" % self.identifier())
        return stmts

    def diff_options(self, newopts):
        """Compare options lists and generate SQL SET or RESET clause

        :newopts: list of new options
        :return: SQL SET / RESET clauses

        Generate ([SET|RESET storage_parameter=value) clauses from two
        lists in the form of 'key=value' strings.
        """
        def to_dict(optlist):
            return dict(opt.split('=', 1) for opt in optlist)

        oldopts = {}
        if self.options is not None:
            oldopts = to_dict(self.options)
        newopts = to_dict(newopts)
        setclauses = []
        for key, val in list(newopts.items()):
            if key not in oldopts:
                setclauses.append("%s=%s" % (key, val))
            elif val != oldopts[key]:
                setclauses.append("%s=%s" % (key, val))
        resetclauses = []
        for key, val in list(oldopts.items()):
            if key not in newopts:
                resetclauses.append("%s" % key)
        clauses = ''
        if setclauses:
            clauses = "SET (%s)" % ', '.join(setclauses)
            if resetclauses:
                clauses += ', '
        if resetclauses:
            clauses += "RESET (%s)" % ', '.join(resetclauses)
        return clauses

    def alter(self, intable):
        """Generate SQL to transform an existing table

        :param intable: a YAML map defining the new table
        :return: list of SQL statements

        Compares the table to an input table and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []
        if len(intable.columns) == 0:
            raise KeyError("Table '%s' has no columns" % intable.name)
        colnames = [col.name for col in self.columns if not col.dropped]
        dbcols = len(colnames)

        colprivs = []
        base = "ALTER %s %s\n    " % (self.objtype, self.qualname())
        # check input columns
        for (num, incol) in enumerate(intable.columns):
            if hasattr(incol, 'oldname'):
                assert(self.columns[num].name == incol.oldname)
                stmts.append(self.columns[num].rename(incol.name))
            # check existing columns
            if num < dbcols and self.columns[num].name == incol.name:
                (stmt, descr) = self.columns[num].alter(incol)
                if stmt:
                    stmts.append(base + stmt)
                colprivs.append(self.columns[num].diff_privileges(incol))
                if descr:
                    stmts.append(descr)
            # add new columns
            elif incol.name not in colnames and not incol.inherited:
                (stmt, descr) = incol.add()
                stmts.append(base + "ADD COLUMN %s" % stmt)
                colprivs.append(incol.add_privs())
                if descr:
                    stmts.append(descr)

        newopts = []
        if intable.options is not None:
            newopts = intable.options
        diff_opts = self.diff_options(newopts)
        if diff_opts:
            stmts.append("ALTER %s %s %s" % (self.objtype, self.identifier(),
                                             diff_opts))
        if colprivs:
            stmts.append(colprivs)
        if intable.tablespace is not None:
            if self.tablespace is None \
                    or self.tablespace != intable.tablespace:
                stmts.append(base + "SET TABLESPACE %s"
                             % quote_id(intable.tablespace))
        elif self.tablespace is not None:
            stmts.append(base + "SET TABLESPACE pg_default")

        stmts.append(super(Table, self).alter(intable))

        return stmts

    def alter_drop_columns(self, intable):
        """Generate SQL to drop columns from an existing table

        :param intable: a YAML map defining the new table
        :return: list of SQL statements

        Compares the table to an input table and generates SQL
        statements to drop any columns missing from the one
        represented by the input.
        """
        if len(intable.columns) == 0:
            raise KeyError("Table '%s' has no columns" % intable.name)
        stmts = []
        incolnames = set(attr.name for attr in intable.columns)
        for attr in self.columns:
            if attr.name not in incolnames:
                if not getattr(attr, 'inherited', False):
                    stmts.append(attr.drop())

        return stmts

    def data_export(self, dbconn, dirpath):
        """Copy table data out to a file

        :param dbconn: database connection to use
        :param dirpath: full path to the directory for the file to be created
        """
        filepath = os.path.join(dirpath, self.extern_filename('data'))
        if self.primary_key is not None:
            order_by = [self.columns[col - 1].name
                        for col in self.primary_key.columns]
        else:
            order_by = ['%d' % (n + 1) for n in range(len(self.columns))]
        dbconn.sql_copy_to(
            "COPY (SELECT * FROM %s ORDER BY %s) TO STDOUT WITH CSV" % (
                self.qualname(), ', '.join(order_by)), filepath)

    def data_import(self, dirpath):
        """Generate SQL to import data into a table

        :param dirpath: full path for the directory for the file
        :return: list of SQL statements
        """
        filepath = os.path.join(dirpath, self.extern_filename('data'))
        stmts = []
        if hasattr(self, '_referred_by'):
            for constr in self._referred_by:
                stmts.append(
                    "ALTER TABLE %s DROP CONSTRAINT %s"
                    % (constr._table.qualname(), constr.name)
                )
        stmts.append("TRUNCATE ONLY %s" % self.qualname())
        stmts.append(("\\copy ", self.qualname(), " from '", filepath,
                      "' csv"))
        if hasattr(self, '_referred_by'):
            for constr in self._referred_by:
                stmts.append(constr.add())
        return stmts

    def get_implied_deps(self, db):
        deps = super(Table, self).get_implied_deps(db)
        for col in self.columns:
            type = db.find_type(col.type)
            if type is not None:
                deps.add(type)

            # Check if the column depends on a sequence to avoid stating the
            # dependency explicitly.
            if col.default is not None:
                m = re.match(r"nextval\('(.*)'::regclass\)", col.default)
                if m:
                    seq = db.tables.find(m.group(1), self.schema)
                    if seq:
                        deps.add(seq)
                        if seq.owner_table is not None:
                            if not hasattr(self, '_owned_seqs'):
                                self._owned_seqs = []
                            self._owned_seqs.append(seq)

        for pname in getattr(self, 'inherits', ()):
            parent = db.tables.find(pname, self.schema)
            assert parent is not None, "couldn't find parent table %s" % pname
            deps.add(parent)

        return deps


OBJTYPES = ['table', 'sequence', 'view', 'materialized view']


class ClassDict(DbObjectDict):
    "The collection of tables and similar objects in a database"

    cls = DbClass

    def _from_catalog(self):
        """Initialize the dictionary of tables by querying the catalogs"""
        self.cls = Table
        for obj in self.fetch():
            self[obj.key()] = obj
            self.by_oid[obj.oid] = obj
        inhtbls = self.dbconn.fetchall(Table.inhquery())
        self.dbconn.rollback()
        for tdata in inhtbls:
            tbl = tdata["sub"]
            partbl = tdata["parent"]
            num = tdata["inhseqno"]
            (sch, tbl) = split_schema_obj(tbl)
            table = self[(sch, tbl)]
            (sch, tbl) = split_schema_obj(partbl)
            if table.schema == sch:
                partbl = tbl
            table.inherits.append(partbl)
        self.cls = Sequence
        for obj in self.fetch():
            self[obj.key()] = obj
            self.by_oid[obj.oid] = obj
            obj.get_attrs(self.dbconn)
            obj.get_dependent_table(self.dbconn)
        from .view import View, MaterializedView
        self.cls = View
        for obj in self.fetch():
            self[obj.key()] = obj
            self.by_oid[obj.oid] = obj
        self.cls = MaterializedView
        for obj in self.fetch():
            self[obj.key()] = obj
            self.by_oid[obj.oid] = obj

    def from_map(self, schema, inobjs, newdb):
        """Initialize the dictionary of tables by converting the input map

        :param schema: schema owning the tables
        :param inobjs: YAML map defining the schema objects
        :param newdb: collection of dictionaries defining the database
        """
        from .view import View, MaterializedView
        for k in inobjs:
            inobj = inobjs[k]
            objtype = None
            for typ in OBJTYPES:
                if k.startswith(typ):
                    objtype = typ
                    key = k[len(typ) + 1:]
            if objtype is None:
                raise KeyError("Unrecognized object type: %s" % k)
            if objtype == 'table':
                self[(schema.name, key)] = table = Table.from_map(
                    key, schema, inobj)
                if inobj and 'inherits' in inobj:
                    table.inherits = inobj.pop('inherits')
                try:
                    newdb.columns.from_map(table, inobj['columns'])
                except KeyError as exc:
                    if table.partition_by is not None:
                        exc.args = ("Table '%s' has no columns" % key, )
                        raise
                newdb.constraints.from_map(table, inobj)
                if 'indexes' in inobj:
                    newdb.indexes.from_map(table, inobj['indexes'])
                if 'rules' in inobj:
                    newdb.rules.from_map(table, inobj['rules'])
                if 'triggers' in inobj:
                    newdb.triggers.from_map(table, inobj['triggers'])
            elif objtype == 'sequence':
                self[(schema.name, key)] = Sequence.from_map(
                    key, schema, inobj)
            elif objtype == 'view':
                self[(schema.name, key)] = view = View.from_map(
                    key, schema, inobj)
                if 'triggers' in inobj:
                    newdb.triggers.from_map(view, inobj['triggers'])
            elif objtype == 'materialized view':
                self[(schema.name, key)] = mview = MaterializedView.from_map(
                    key, schema, inobj)
                if 'indexes' in inobj:
                    newdb.indexes.from_map(mview, inobj['indexes'])
            else:
                raise KeyError("Unrecognized object type: %s" % k)
            obj = self[(schema.name, key)]
            if 'depends_on' in inobj:
                obj.depends_on.extend(inobj['depends_on'])

    def find(self, obj, schema=None):
        """Find a table given its name.

        The name can contain array type modifiers such as '[]'

        Return None if not found.
        """
        sch, name = split_schema_obj(obj, schema)
        name = name.rstrip('[]')
        return self.get((sch, name))

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
        seqs = [self[t] for t in self if isinstance(self[t], Sequence)]
        for (sch, tbl) in dbcolumns:
            if (sch, tbl) in self:
                #assert isinstance(self[(sch, tbl)], Table)
                self[(sch, tbl)].columns = dbcolumns[(sch, tbl)]
                for col in dbcolumns[(sch, tbl)]:
                    col._table = self[(sch, tbl)]
                    if col.identity is not None:
                        for seq in seqs:
                            if col.table == seq.owner_table and \
                               col.name == seq.owner_column:
                                col._owner_seq = seq
                                seq._owner_col = col

        # Normalize owner_column's to column names
        for (sch, tbl) in self:
            table = self[(sch, tbl)]
            if isinstance(table, Sequence) and table.owner_table is not None:
                if isinstance(table.owner_column, int):
                    table.owner_column = self[(sch, table.owner_table)]. \
                        column_names()[table.owner_column - 1]

        for (sch, tbl, cns) in dbconstrs:
            constr = dbconstrs[(sch, tbl, cns)]
            if isinstance(constr, CheckConstraint) and constr.is_domain_check:
                continue
            assert self[(sch, tbl)]
            constr._table = table = self[(sch, tbl)]
            if isinstance(constr, CheckConstraint):
                table.check_constraints.update({cns: constr})
            elif isinstance(constr, PrimaryKey):
                table.primary_key = constr
            elif isinstance(constr, ForeignKey):
                # link referenced and referrer
                constr._references = self[(
                    constr.ref_schema, constr.ref_table)]
                self[
                    (constr.ref_schema, constr.ref_table)
                ]._referred_by.append(constr)
                table.foreign_keys.update({cns: constr})
            elif isinstance(constr, UniqueConstraint):
                table.unique_constraints.update({cns: constr})

        def link_one(targdict, schema, tbl, objkey, objtype):
            table = self[(schema, tbl)]
            if not hasattr(table, objtype):
                setattr(table, objtype, {})
            objdict = getattr(table, objtype)
            objdict.update({objkey: targdict[(schema, tbl, objkey)]})

        for (sch, tbl, idx) in dbindexes:
            link_one(dbindexes, sch, tbl, idx, 'indexes')
        for (sch, tbl, rul) in dbrules:
            link_one(dbrules, sch, tbl, rul, 'rules')
            dbrules[(sch, tbl, rul)]._table = self[(sch, tbl)]
        for (sch, tbl, trg) in dbtriggers:
            link_one(dbtriggers, sch, tbl, trg, 'triggers')
            dbtriggers[(sch, tbl, trg)]._table = self[(sch, tbl)]
