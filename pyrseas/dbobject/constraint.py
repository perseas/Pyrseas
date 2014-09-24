# -*- coding: utf-8 -*-
"""
    pyrseas.constraint
    ~~~~~~~~~~~~~~~~~~

    This module defines six classes: Constraint derived from
    DbSchemaObject, CheckConstraint, PrimaryKey, ForeignKey and
    UniqueConstraint derived from Constraint, and ConstraintDict
    derived from DbObjectDict.
"""
from collections import defaultdict

from pyrseas.dbobject import DbObjectDict, DbSchemaObject
from pyrseas.dbobject import quote_id, split_schema_obj, commentable


ACTIONS = {'r': 'restrict', 'c': 'cascade', 'n': 'set null',
           'd': 'set default'}


class Constraint(DbSchemaObject):
    """A constraint definition, such as a primary key, foreign key or
       unique constraint"""

    keylist = ['schema', 'table', 'name']
    catalog_table = 'pg_constraint'

    def __init__(self, schema, table, **kwargs):
        self._table_qualname = '%s.%s' % (quote_id(schema), quote_id(table))
        super(Constraint, self).__init__(schema=schema, table=table, **kwargs)

    def key_columns(self):
        """Return comma-separated list of key column names

        :return: string
        """
        return ", ".join([quote_id(col) for col in self.keycols])

    @commentable
    def add(self):
        """Return string to add the constraint via ALTER TABLE

        :return: SQL statement

        Works as is for primary keys and unique constraints but has
        to be overridden for check constraints and foreign keys.
        """
        stmts = []
        tblspc = ''
        if hasattr(self, 'tablespace'):
            tblspc = " USING INDEX TABLESPACE %s" % self.tablespace
        stmts.append("ALTER TABLE %s ADD CONSTRAINT %s %s (%s)%s" % (
                     self._table_qualname, quote_id(self.name),
                     self.objtype, self.key_columns(), tblspc))
        if hasattr(self, 'cluster') and self.cluster:
            stmts.append("CLUSTER %s USING %s" % (
                quote_id(self.table), quote_id(self.name)))
        return stmts

    def drop(self):
        """Return string to drop the constraint via ALTER TABLE

        :return: SQL statement
        """
        if not hasattr(self, 'dropped') or not self.dropped:
            self.dropped = True
            return "ALTER TABLE %s DROP CONSTRAINT %s" % (
                self._table_qualname, quote_id(self.name))
        return []

    def comment(self):
        """Return SQL statement to create COMMENT on constraint

        :return: SQL statement
        """
        return "COMMENT ON CONSTRAINT %s ON %s IS %s" % (
            quote_id(self.name), self._table_qualname, self._comment_text())

    def get_implied_deps(self, db):
        deps = super(Constraint, self).get_implied_deps(db)

        # add the table we are defined into
        try:
            deps.add(db.tables[self.schema, self.table])
        except KeyError:
            # mmm... maybe it was a type then?
            # but the types work in a different way and it's the type to
            # depend on the costraint, so we don't do anything
            assert db.types[self.schema, self.table]

        return deps


class CheckConstraint(Constraint):
    "A check constraint definition"

    objtype = "CHECK"

    def to_map(self, db, dbcols):
        """Convert a check constraint definition to a YAML-suitable format

        :param dbcols: dictionary of dbobject columns
        :return: dictionary
        """
        dct = self._base_map(db)
        if 'target' in dct:
            del dct['target']
        if dbcols:
            dct['columns'] = [dbcols[k - 1] for k in self.keycols]
            del dct['keycols']
        return {self.name: dct}

    @commentable
    def add(self):
        """Return string to add the CHECK constraint via ALTER TABLE

        :return: SQL statement
        """
        return ["ALTER TABLE %s ADD CONSTRAINT %s %s (%s)" % (
                self._table_qualname, quote_id(self.name), self.objtype,
                self.expression)]

    def diff_map(self, inchk):
        """Generate SQL to transform an existing CHECK constraint

        :param inchk: a YAML map defining the new CHECK constraint
        :return: list of SQL statements

        Compares the CHECK constraint to an input constraint and generates
        SQL statements to transform it into the one represented by the
        input.
        """
        stmts = []
        # TODO: to be implemented
        stmts.append(self.diff_description(inchk))
        return stmts


class PrimaryKey(Constraint):
    "A primary key constraint definition"

    objtype = "PRIMARY KEY"

    def to_map(self, db, dbcols):
        """Convert a primary key definition to a YAML-suitable format

        :param dbcols: dictionary of dbobject columns
        :return: dictionary
        """
        dct = self._base_map(db)
        if dct['access_method'] == 'btree':
            del dct['access_method']
        dct['columns'] = [dbcols[k - 1] for k in self.keycols]
        del dct['keycols']
        return {self.name: dct}

    def diff_map(self, inpk):
        """Generate SQL to transform an existing primary key

        :param inpk: a YAML map defining the new primary key
        :return: list of SQL statements

        Compares the primary key to an input primary key and generates
        SQL statements to transform it into the one represented by the
        input.
        """
        stmts = []
        # TODO: to be implemented (via ALTER DROP and ALTER ADD)
        if hasattr(inpk, 'cluster'):
            if not hasattr(self, 'cluster'):
                stmts.append("CLUSTER %s USING %s" % (
                    quote_id(self.table), quote_id(self.name)))
        elif hasattr(self, 'cluster'):
            stmts.append("ALTER TABLE %s\n    SET WITHOUT CLUSTER" %
                         quote_id(self.table))
        stmts.append(self.diff_description(inpk))
        return stmts


class ForeignKey(Constraint):
    "A foreign key constraint definition"

    objtype = "FOREIGN KEY"

    def ref_columns(self):
        """Return comma-separated list of reference column names

        :return: string
        """
        return ", ".join(self.ref_cols)

    def to_map(self, db, dbcols, refcols):
        """Convert a foreign key definition to a YAML-suitable format

        :param dbcols: dictionary of dbobject columns
        :return: dictionary
        """
        dct = self._base_map(db)
        dct['columns'] = [dbcols[k - 1] for k in self.keycols]
        del dct['keycols']
        refsch = hasattr(self, 'ref_schema') and self.ref_schema or self.schema
        ref_cols = [refcols[k - 1] for k in self.ref_cols]
        dct['references'] = {'table': dct['ref_table'], 'columns': ref_cols}
        if 'ref_schema' in dct:
            dct['references'].update(schema=refsch)
            del dct['ref_schema']
        del dct['ref_table'], dct['ref_cols']
        return {self.name: dct}

    @commentable
    def add(self):
        """Return string to add the foreign key via ALTER TABLE

        :return: SQL statement
        """
        match = ''
        if hasattr(self, 'match'):
            match = " MATCH %s" % self.match.upper()
        actions = ''
        if hasattr(self, 'on_update'):
            actions = " ON UPDATE %s" % self.on_update.upper()
        if hasattr(self, 'on_delete'):
            actions += " ON DELETE %s" % self.on_delete.upper()
        if getattr(self, 'deferrable', False):
            actions += " DEFERRABLE"
        if getattr(self, 'deferred', False):
            actions += " INITIALLY DEFERRED"

        return "ALTER TABLE %s ADD CONSTRAINT %s FOREIGN KEY (%s) " \
            "REFERENCES %s.%s (%s)%s%s" % (
            self._table_qualname, quote_id(self.name), self.key_columns(),
            quote_id(self.ref_schema), quote_id(self.ref_table),
            self.ref_columns(), match, actions)

    def diff_map(self, infk):
        """Generate SQL to transform an existing foreign key

        :param infk: a YAML map defining the new foreign key
        :return: list of SQL statements

        Compares the foreign key to an input foreign key and generates
        SQL statements to transform it into the one represented by the
        input.
        """
        stmts = []
        # TODO: to be implemented (via ALTER DROP and ALTER ADD)
        stmts.append(self.diff_description(infk))
        return stmts

    def get_implied_deps(self, db):
        deps = super(ForeignKey, self).get_implied_deps(db)

        # add the table we reference
        deps.add(db.tables[self.ref_schema, self.ref_table])

        return deps


class UniqueConstraint(Constraint):
    "A unique constraint definition"

    objtype = "UNIQUE"

    def to_map(self, db, dbcols):
        """Convert a unique constraint definition to a YAML-suitable format

        :param dbcols: dictionary of dbobject columns
        :return: dictionary
        """
        dct = self._base_map(db)
        if dct['access_method'] == 'btree':
            del dct['access_method']
        dct['columns'] = []
        dct['columns'] = [dbcols[k - 1] for k in self.keycols]
        del dct['keycols']
        return {self.name: dct}

    def diff_map(self, inuc):
        """Generate SQL to transform an existing unique constraint

        :param inuc: a YAML map defining the new unique constraint
        :return: list of SQL statements

        Compares the unique constraint to an input unique constraint
        and generates SQL statements to transform it into the one
        represented by the input.
        """
        stmts = []
        # TODO: to be implemented (via ALTER DROP and ALTER ADD)
        if hasattr(inuc, 'cluster'):
            if not hasattr(self, 'cluster'):
                stmts.append("CLUSTER %s USING %s" % (
                    quote_id(self.table), quote_id(self.name)))
        elif hasattr(self, 'cluster'):
            stmts.append("ALTER TABLE %s\n    SET WITHOUT CLUSTER" %
                         quote_id(self.table))
        stmts.append(self.diff_description(inuc))
        return stmts

MATCHTYPES_PRE93 = {'f': 'full', 'p': 'partial', 'u': 'simple'}
COMMON_ATTRS = ['access_method', 'tablespace', 'description', 'cluster']


class ConstraintDict(DbObjectDict):
    "The collection of table or column constraints in a database"

    cls = Constraint
    query = \
        """SELECT c.oid,
                  nspname AS schema,
                  CASE WHEN contypid = 0 THEN conrelid::regclass::text
                       ELSE contypid::regtype::text END AS table,
                  conname AS name,
                  CASE WHEN contypid != 0 THEN 'd' ELSE '' END AS target,
                  contype AS type, conkey AS keycols,
                  condeferrable AS deferrable, condeferred AS deferred,
                  confrelid::regclass AS ref_table, confkey AS ref_cols,
                  consrc AS expression, confupdtype AS on_update,
                  confdeltype AS on_delete, confmatchtype AS match,
                  amname AS access_method, spcname AS tablespace,
                  indisclustered AS cluster,
                  obj_description(c.oid, 'pg_constraint') AS description
           FROM pg_constraint c
                JOIN pg_namespace ON (connamespace = pg_namespace.oid)
                LEFT JOIN pg_class cl on (conname = relname)
                LEFT JOIN pg_index i ON (i.indexrelid = cl.oid)
                LEFT JOIN pg_tablespace t ON (cl.reltablespace = t.oid)
                LEFT JOIN pg_am on (relam = pg_am.oid)
           WHERE (nspname != 'pg_catalog' AND nspname != 'information_schema')
                 AND conislocal
           ORDER BY schema, "table", name"""
    match_types = {'f': 'full', 'p': 'partial', 's': 'simple'}

    def _from_catalog(self):
        """Initialize the dictionary of constraints by querying the catalogs"""
        if self.dbconn.version < 90300:
            self.match_types = MATCHTYPES_PRE93
        for constr in self.fetch():
            constr.unqualify()
            oid = constr.oid
            sch, tbl, cns = constr.key()
            sch, tbl = split_schema_obj('%s.%s' % (sch, tbl))
            constr_type = constr.type
            del constr.type
            if constr_type != 'f':
                del constr.ref_table
                del constr.on_update
                del constr.on_delete
                del constr.match
            if constr_type == 'c':
                self.by_oid[oid] = self[(sch, tbl, cns)] \
                    = CheckConstraint(**constr.__dict__)
            elif constr_type == 'p':
                self.by_oid[oid] =self[(sch, tbl, cns)] \
                    = PrimaryKey(**constr.__dict__)
            elif constr_type == 'f':
                # normalize reference schema/table:
                # if reftbl is qualified, split the schema out,
                # otherwise it's in the 'public' schema (set as default
                # when connecting)
                if constr.on_update == 'a':
                    del constr.on_update
                else:
                    constr.on_update = ACTIONS[constr.on_update]
                if constr.on_delete == 'a':
                    del constr.on_delete
                else:
                    constr.on_delete = ACTIONS[constr.on_delete]
                if self.match_types[constr.match] == 'simple':
                    del constr.match
                else:
                    constr.match = self.match_types[constr.match]
                reftbl = constr.ref_table
                (constr.ref_schema, constr.ref_table) = split_schema_obj(
                    reftbl)
                self.by_oid[oid] = self[(sch, tbl, cns)] \
                    = ForeignKey(**constr.__dict__)
            elif constr_type == 'u':
                self.by_oid[oid] = self[(sch, tbl, cns)] \
                    = UniqueConstraint(**constr.__dict__)

    def from_map(self, table, inconstrs, target=''):
        """Initialize the dictionary of constraints by converting the input map

        :param table: table affected by the constraints
        :param inconstrs: YAML map defining the constraints
        """
        if 'check_constraints' in inconstrs:
            chks = inconstrs['check_constraints']
            for cns in chks:
                check = CheckConstraint(table=table.name, schema=table.schema,
                                        name=cns)
                val = chks[cns]
                try:
                    check.expression = val['expression']
                except KeyError as exc:
                    exc.args = ("Constraint '%s' is missing expression"
                                % cns, )
                    raise
                check.depends_on.extend(val.get('depends_on', ()))
                if check.expression[0] == '(' and check.expression[-1] == ')':
                    check.expression = check.expression[1:-1]
                if 'columns' in val:
                    check.keycols = val['columns']
                if target:
                    check.target = target
                if 'description' in val:
                    check.description = val['description']
                self[(table.schema, table.name, cns)] = check
        if 'primary_key' in inconstrs:
            cns = list(inconstrs['primary_key'].keys())[0]
            pkey = PrimaryKey(table=table.name, schema=table.schema,
                              name=cns)
            val = inconstrs['primary_key'][cns]
            try:
                pkey.keycols = val['columns']
            except KeyError as exc:
                exc.args = ("Constraint '%s' is missing columns" % cns, )
                raise
            for attr, value in list(val.items()):
                if attr in COMMON_ATTRS:
                    setattr(pkey, attr, value)
            self[(table.schema, table.name, cns)] = pkey
        if 'foreign_keys' in inconstrs:
            fkeys = inconstrs['foreign_keys']
            for cns in fkeys:
                fkey = ForeignKey(table=table.name, schema=table.schema,
                                  name=cns)
                val = fkeys[cns]
                fkey.depends_on.extend(val.get('depends_on', ()))
                if 'on_update' in val:
                    act = val['on_update']
                    if act.lower() not in list(ACTIONS.values()):
                        raise ValueError("Invalid action '%s' for constraint "
                                         "'%s'" % (act, cns))
                    fkey.on_update = act
                if 'on_delete' in val:
                    act = val['on_delete']
                    if act.lower() not in list(ACTIONS.values()):
                        raise ValueError("Invalid action '%s' for constraint "
                                         "'%s'" % (act, cns))
                    fkey.on_delete = act
                if 'deferrable' in val:
                    fkey.deferrable = True
                if 'deferred' in val:
                    fkey.deferred = True
                if 'match' in val:
                    mat = val['match']
                    if mat.lower() not in list(self.match_types.values()):
                        raise ValueError("Invalid match type '%s' for "
                                         "constraint '%s'" % (mat, cns))
                    fkey.match = mat
                try:
                    fkey.keycols = val['columns']
                except KeyError as exc:
                    exc.args = ("Constraint '%s' is missing columns" % cns, )
                    raise
                try:
                    refs = val['references']
                except KeyError as exc:
                    exc.args = ("Constraint '%s' missing references" % cns, )
                    raise
                try:
                    fkey.ref_table = refs['table']
                except KeyError as exc:
                    exc.args = ("Constraint '%s' missing table reference"
                                % cns, )
                    raise
                try:
                    fkey.ref_cols = refs['columns']
                except KeyError as exc:
                    exc.args = ("Constraint '%s' missing reference columns"
                                % cns, )
                    raise
                sch = table.schema
                if 'schema' in refs:
                    sch = refs['schema']
                fkey.ref_schema = sch
                if 'description' in val:
                    fkey.description = val['description']
                self[(table.schema, table.name, cns)] = fkey
        if 'unique_constraints' in inconstrs:
            uconstrs = inconstrs['unique_constraints']
            for cns in uconstrs:
                unq = UniqueConstraint(table=table.name, schema=table.schema,
                                       name=cns)
                val = uconstrs[cns]
                try:
                    unq.keycols = val['columns']
                except KeyError as exc:
                    exc.args = ("Constraint '%s' is missing columns" % cns, )
                    raise
                for attr, value in list(val.items()):
                    if attr in COMMON_ATTRS:
                        setattr(unq, attr, value)
                self[(table.schema, table.name, cns)] = unq

    def diff_map(self, inconstrs):
        """Generate SQL to transform existing constraints

        :param inconstrs: a YAML map defining the new constraints
        :return: list of SQL statements

        Compares the existing constraint definitions, as fetched from
        the catalogs, to the input map and generates SQL statements to
        transform the constraints accordingly.
        """
        return super(ConstraintDict, self).diff_map(inconstrs)

    def _diff_map(self, inconstrs):
        stmts = defaultdict(list)
        # foreign keys are processed in a second pass
        # constraints cannot be renamed
        for turn in (1, 2):
            # check database constraints
            for (sch, tbl, cns) in self:
                constr = self[(sch, tbl, cns)]
                if isinstance(constr, ForeignKey):
                    if turn == 1:
                        continue
                elif turn == 2:
                    continue
                # if missing, drop it
                if (sch, tbl, cns) not in inconstrs \
                        and not hasattr(constr, 'target'):
                    stmts[constr].append(constr.drop())
            # check input constraints
            for (sch, tbl, cns) in inconstrs:
                inconstr = inconstrs[(sch, tbl, cns)]
                # skip DOMAIN constraints
                if hasattr(inconstr, 'target'):
                    continue
                if isinstance(inconstr, ForeignKey):
                    if turn == 1:
                        continue
                elif turn == 2:
                    continue
                # does it exist in the database?
                if (sch, tbl, cns) not in self:
                    # add the new constraint
                    stmts[inconstr].append(inconstr.add())
                else:
                    # check constraint objects
                    stmts[inconstr].append(self[(sch, tbl, cns)].diff_map(inconstr))

        return stmts
