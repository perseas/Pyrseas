# -*- coding: utf-8 -*-
"""
    pyrseas.constraint
    ~~~~~~~~~~~~~~~~~~

    This module defines six classes: Constraint derived from
    DbSchemaObject, CheckConstraint, PrimaryKey, ForeignKey and
    UniqueConstraint derived from Constraint, and ConstraintDict
    derived from DbObjectDict.
"""
from pyrseas.dbobject import DbObjectDict, DbSchemaObject
from pyrseas.dbobject import quote_id, split_schema_obj, commentable


ACTIONS = {'r': 'restrict', 'c': 'cascade', 'n': 'set null',
           'd': 'set default'}


class Constraint(DbSchemaObject):
    """A constraint definition, such as a primary key, foreign key or
       unique constraint"""

    keylist = ['schema', 'table', 'name']

    def key_columns(self):
        """Return comma-separated list of key column names

        :return: string
        """
        return ", ".join([quote_id(col) for col in self.col_names])

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
                     self._table.qualname(), quote_id(self.name),
                     self.objtype, self.key_columns(), tblspc))
        if hasattr(self, 'cluster') and self.cluster:
            stmts.append("CLUSTER %s USING %s" % (
                self._table.qualname(), quote_id(self.name)))
        return stmts

    def drop(self):
        """Return string to drop the constraint via ALTER TABLE

        :return: SQL statement
        """
        if not hasattr(self, 'dropped') or not self.dropped:
            self.dropped = True
            return "ALTER TABLE %s DROP CONSTRAINT %s" % (
                self._table.qualname(), quote_id(self.name))
        return []

    def comment(self):
        """Return SQL statement to create COMMENT on constraint

        :return: SQL statement
        """
        return "COMMENT ON CONSTRAINT %s ON %s IS %s" % (
            quote_id(self.name), self._table.qualname(), self._comment_text())


class CheckConstraint(Constraint):
    "A check constraint definition"

    objtype = "CHECK"

    def to_map(self, dbcols):
        """Convert a check constraint definition to a YAML-suitable format

        :param dbcols: dictionary of dbobject columns
        :return: dictionary
        """
        dct = self._base_map()
        if '_table' in dct:
            del dct['_table']
        if 'target' in dct:
            del dct['target']
        if dbcols:
            dct['columns'] = [dbcols[k - 1] for k in self.col_idx]
            del dct['col_idx']
        return {self.name: dct}

    @commentable
    def add(self):
        """Return string to add the CHECK constraint via ALTER TABLE

        :return: SQL statement
        """
        return ["ALTER TABLE %s ADD CONSTRAINT %s %s (%s)" % (
                self._table.qualname(), quote_id(self.name), self.objtype,
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

    def to_map(self, dbcols):
        """Convert a primary key definition to a YAML-suitable format

        :param dbcols: dictionary of dbobject columns
        :return: dictionary
        """
        dct = self._base_map()
        if dct['access_method'] == 'btree':
            del dct['access_method']
        del dct['_table']
        dct['columns'] = [dbcols[k - 1] for k in self.col_idx]
        del dct['col_idx']
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

        # TODO chompare column names
        if self.col_idx != inpk.col_idx:
            stmts.append(self.drop())
            stmts.append(inpk.add())
        elif hasattr(inpk, 'cluster'):
            if not hasattr(self, 'cluster'):
                stmts.append("CLUSTER %s USING %s" % (
                    self._table.qualname(), quote_id(self.name)))
        elif hasattr(self, 'cluster'):
            stmts.append("ALTER TABLE %s\n    SET WITHOUT CLUSTER" %
                         self._table.qualname())
        stmts.append(self.diff_description(inpk))
        return stmts


class ForeignKey(Constraint):
    "A foreign key constraint definition"

    objtype = "FOREIGN KEY"

    def ref_columns(self):
        """Return comma-separated list of reference column names

        :return: string
        """
        return ", ".join(self.ref_col_names)

    def to_map(self, dbcols, refcols):
        """Convert a foreign key definition to a YAML-suitable format

        :param dbcols: dictionary of dbobject columns
        :return: dictionary
        """
        dct = self._base_map()
        del dct['_table']
        dct['columns'] = [dbcols[k - 1] for k in self.col_idx]
        del dct['col_idx']
        refsch = hasattr(self, 'ref_schema') and self.ref_schema or self.schema
        ref_col_names = [refcols[k - 1] for k in self.ref_col_idxs]
        dct['references'] = {'table': dct['ref_table'], 'columns': ref_col_names}
        if 'ref_schema' in dct:
            dct['references'].update(schema=refsch)
            del dct['ref_schema']
        del dct['ref_table'], dct['ref_col_idxs']
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
            "REFERENCES %s (%s)%s%s" % (
            self._table.qualname(), quote_id(self.name), self.key_columns(),
            self.references.qualname(), self.ref_columns(), match, actions)

    def diff_map(self, infk):
        """Generate SQL to transform an existing foreign key

        :param infk: a YAML map defining the new foreign key
        :return: list of SQL statements

        Compares the foreign key to an input foreign key and generates
        SQL statements to transform it into the one represented by the
        input.
        """
        stmts = []

        # TODO compare column names
        changed = self.col_idx != infk.col_idx or \
                (self.ref_col_idxs!= infk.ref_col_idxs)

        for act in ['on_update', 'on_delete']:
            s_act = getattr(self, act).upper() if hasattr(self, act) else None
            in_act = getattr(infk, act).upper() if hasattr(infk, act) else None
            if s_act != in_act:
                changed = True

        if changed:
            stmts.append(self.drop())
            stmts.append(infk.add())

        stmts.append(self.diff_description(infk))
        return stmts


class UniqueConstraint(Constraint):
    "A unique constraint definition"

    objtype = "UNIQUE"

    def to_map(self, dbcols):
        """Convert a unique constraint definition to a YAML-suitable format

        :param dbcols: dictionary of dbobject columns
        :return: dictionary
        """
        dct = self._base_map()
        if dct['access_method'] == 'btree':
            del dct['access_method']
        del dct['_table']
        dct['columns'] = []
        dct['columns'] = [dbcols[k - 1] for k in self.col_idx]
        del dct['col_idx']
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
        if self.col_idx != inuc.col_idx:
            stmts.append(self.drop())
            stmts.append(inuc.add())
        elif hasattr(inuc, 'cluster'):
            if not hasattr(self, 'cluster'):
                stmts.append("CLUSTER %s USING %s" % (
                    self._table.qualname(), quote_id(self.name)))
        elif hasattr(self, 'cluster'):
            stmts.append("ALTER TABLE %s\n    SET WITHOUT CLUSTER" %
                         self._table.qualname())
        stmts.append(self.diff_description(inuc))
        return stmts

MATCHTYPES_PRE93 = {'f': 'full', 'p': 'partial', 'u': 'simple'}
COMMON_ATTRS = ['access_method', 'tablespace', 'description', 'cluster']


class ConstraintDict(DbObjectDict):
    "The collection of table or column constraints in a database"

    cls = Constraint
    query = \
        """SELECT nspname AS schema,
                  CASE WHEN contypid = 0 THEN conrelid::regclass::text
                       ELSE contypid::regtype::text END AS table,
                  conname AS name,
                  CASE WHEN contypid != 0 THEN 'd' ELSE '' END AS target,
                  contype AS type, conkey AS col_idx,
                  condeferrable AS deferrable, condeferred AS deferred,
                  confrelid::regclass AS ref_table, confkey AS ref_col_idxs,
                  consrc AS expression, confupdtype AS on_update,
                  confdeltype AS on_delete, confmatchtype AS match,
                  amname AS access_method, spcname AS tablespace,
                  indisclustered AS cluster, coninhcount > 0 AS inherited,
                  obj_description(c.oid, 'pg_constraint') AS description
           FROM pg_constraint c
                JOIN pg_namespace ON (connamespace = pg_namespace.oid)
                LEFT JOIN pg_class cl on (conname = relname)
                LEFT JOIN pg_index i ON (i.indexrelid = cl.oid)
                LEFT JOIN pg_tablespace t ON (cl.reltablespace = t.oid)
                LEFT JOIN pg_am on (relam = pg_am.oid)
           WHERE (nspname != 'pg_catalog' AND nspname != 'information_schema')
           ORDER BY schema, 2, name"""
    match_types = {'f': 'full', 'p': 'partial', 's': 'simple'}

    def _from_catalog(self):
        """Initialize the dictionary of constraints by querying the catalogs"""
        if self.dbconn.version < 90300:
            self.match_types = MATCHTYPES_PRE93
        for constr in self.fetch():
            constr.unqualify()
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
                self[(sch, tbl, cns)] = CheckConstraint(**constr.__dict__)
            elif constr_type == 'p':
                self[(sch, tbl, cns)] = PrimaryKey(**constr.__dict__)
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
                self[(sch, tbl, cns)] = ForeignKey(**constr.__dict__)
            elif constr_type == 'u':
                self[(sch, tbl, cns)] = UniqueConstraint(**constr.__dict__)

    @classmethod
    def _get_col_idx(cls, col_map_list, col_names):
        columns = [list(col.keys())[0] for col in col_map_list]
        return [columns.index(c) + 1 for c in col_names]

    def from_map(self, table, inconstrs, target='', rtables=None):
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
                if check.expression[0] == '(' and check.expression[-1] == ')':
                    check.expression = check.expression[1:-1]
                if 'columns' in val:
                    check.col_names = val['columns']
                if target:
                    check.target = target
                if 'description' in val:
                    check.description = val['description']
                if 'inherited' in val:
                    check.inherited = val['inherited']
                self[(table.schema, table.name, cns)] = check
        if 'primary_key' in inconstrs:
            cns = list(inconstrs['primary_key'].keys())[0]
            pkey = PrimaryKey(table=table.name, schema=table.schema,
                              name=cns)
            val = inconstrs['primary_key'][cns]
            try:
                pkey.col_names = val['columns']
                pkey.col_idx = self._get_col_idx(inconstrs['columns'],
                                                 pkey.col_names)
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
                    fkey.col_names = val['columns']
                    fkey.col_idx = self._get_col_idx(inconstrs['columns'],
                                                     fkey.col_names)
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
                    fkey.ref_col_names = refs['columns']
                    rtable_key = 'table ' + fkey.ref_table
                    if rtables and rtable_key in rtables:
                        ref_table = rtables[rtable_key]
                        fkey.ref_col_idxs = \
                            self._get_col_idx(ref_table['columns'],
                                              fkey.ref_col_names)
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
                    unq.col_names = val['columns']
                    unq.col_idx = self._get_col_idx(inconstrs['columns'],
                                                     unq.col_names)
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
        stmts = []
        # foreign keys are processed in a second pass
        # constraints cannot be renamed
        for turn in (1, 2):
            # check database constraints
            for (sch, tbl, cns) in self:
                constr = self[(sch, tbl, cns)]
                # ignore inherited constraints
                if getattr(constr, 'inherited', False):
                    continue
                if isinstance(constr, ForeignKey):
                    if turn == 1:
                        continue
                elif turn == 2:
                    continue
                # if missing, drop it
                if (sch, tbl, cns) not in inconstrs \
                        and not hasattr(constr, 'target'):
                    stmts.append(constr.drop())
            # check input constraints
            for (sch, tbl, cns) in inconstrs:
                inconstr = inconstrs[(sch, tbl, cns)]
                # ignore inherited constraints, take 2
                if getattr(inconstr, 'inherited', False):
                    continue
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
                    stmts.append(inconstr.add())
                else:
                    # check constraint objects
                    stmts.append(self[(sch, tbl, cns)].diff_map(inconstr))

        return stmts
