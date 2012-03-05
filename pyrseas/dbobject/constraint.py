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
from pyrseas.dbobject import quote_id, split_schema_obj


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
        return ", ".join([quote_id(col) for col in self.keycols])

    def add(self):
        """Return string to add the constraint via ALTER TABLE

        :return: SQL statement

        Works as is for primary keys and unique constraints but has
        to be overridden for check constraints and foreign keys.
        """
        stmts = ["ALTER TABLE %s ADD CONSTRAINT %s %s (%s)" % (
                self._table.qualname(), quote_id(self.name),
                self.objtype, self.key_columns())]
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts

    def drop(self):
        """Return string to drop the constraint via ALTER TABLE

        :return: SQL statement
        """
        if not hasattr(self, 'dropped') or not self.dropped:
            self.dropped = True
            return "ALTER TABLE %s DROP CONSTRAINT %s" % (
                self._table.qualname(), self.name)
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
            dct['columns'] = [dbcols[k - 1] for k in self.keycols]
            del dct['keycols']
        return {self.name: dct}

    def add(self):
        """Return string to add the CHECK constraint via ALTER TABLE

        :return: SQL statement
        """
        stmts = ["ALTER TABLE %s ADD CONSTRAINT %s %s (%s)" % (
                self._table.qualname(), self.name, self.objtype,
                self.expression)]
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        return stmts

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
        del dct['_table']
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

    def to_map(self, dbcols, refcols):
        """Convert a foreign key definition to a YAML-suitable format

        :param dbcols: dictionary of dbobject columns
        :return: dictionary
        """
        dct = self._base_map()
        del dct['_table']
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

    def add(self):
        """Return string to add the foreign key via ALTER TABLE

        :return: SQL statement
        """
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
            "REFERENCES %s (%s)%s" % (
            self._table.qualname(), self.name, self.key_columns(),
            self.references.qualname(), self.ref_columns(), actions)

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


class UniqueConstraint(Constraint):
    "A unique constraint definition"

    objtype = "UNIQUE"

    def to_map(self, dbcols):
        """Convert a unique constraint definition to a YAML-suitable format

        :param dbcols: dictionary of dbobject columns
        :return: dictionary
        """
        dct = self._base_map()
        del dct['_table']
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
        stmts.append(self.diff_description(inuc))
        return stmts


class ConstraintDict(DbObjectDict):
    "The collection of table or column constraints in a database"

    cls = Constraint
    query = \
        """SELECT nspname AS schema,
                  CASE WHEN contypid = 0 THEN conrelid::regclass::name
                       ELSE contypid::regtype::name END AS table,
                  conname AS name,
                  CASE WHEN contypid != 0 THEN 'd' ELSE '' END AS target,
                  contype AS type, conkey AS keycols,
                  condeferrable AS deferrable,
                  condeferred AS deferred,
                  confrelid::regclass AS ref_table, confkey AS ref_cols,
                  consrc AS expression, confupdtype AS on_update,
                  confdeltype AS on_delete, amname AS access_method,
                  obj_description(c.oid, 'pg_constraint') AS description
           FROM pg_constraint c
                JOIN pg_namespace ON (connamespace = pg_namespace.oid)
                LEFT JOIN pg_class on (conname = relname)
                LEFT JOIN pg_am on (relam = pg_am.oid)
           WHERE (nspname != 'pg_catalog' AND nspname != 'information_schema')
                 AND conislocal
           ORDER BY schema, 2, name"""

    def _from_catalog(self):
        """Initialize the dictionary of constraints by querying the catalogs"""
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
                reftbl = constr.ref_table
                (constr.ref_schema, constr.ref_table) = split_schema_obj(
                    reftbl)
                self[(sch, tbl, cns)] = ForeignKey(**constr.__dict__)
            elif constr_type == 'u':
                self[(sch, tbl, cns)] = UniqueConstraint(**constr.__dict__)

    def from_map(self, table, inconstrs, target=''):
        """Initialize the dictionary of constraints by converting the input map

        :param table: table affected by the constraints
        :param inconstrs: YAML map defining the constraints
        """
        if 'check_constraints' in inconstrs:
            chks = inconstrs['check_constraints']
            for cns in chks.keys():
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
            if 'access_method' in val:
                pkey.access_method = val['access_method']
            if 'description' in val:
                pkey.description = val['description']
            self[(table.schema, table.name, cns)] = pkey
        if 'foreign_keys' in inconstrs:
            fkeys = inconstrs['foreign_keys']
            for cns in fkeys.keys():
                fkey = ForeignKey(table=table.name, schema=table.schema,
                                      name=cns)
                val = fkeys[cns]
                if 'on_update' in val:
                    act = val['on_update']
                    if act.lower() not in ACTIONS.values():
                        raise ValueError("Invalid action '%s' for constraint "
                                         "'%s'" % (act, cns))
                    fkey.on_update = act
                if 'on_delete' in val:
                    act = val['on_delete']
                    if act.lower() not in ACTIONS.values():
                        raise ValueError("Invalid action '%s' for constraint "
                                         "'%s'" % (act, cns))
                    fkey.on_delete = act
                if 'deferrable' in val:
                    fkey.deferrable = True
                if 'deferred' in val:
                    fkey.deferred = True
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
            for cns in uconstrs.keys():
                unq = UniqueConstraint(table=table.name, schema=table.schema,
                                      name=cns)
                val = uconstrs[cns]
                try:
                    unq.keycols = val['columns']
                except KeyError as exc:
                    exc.args = ("Constraint '%s' is missing columns" % cns, )
                    raise
                if 'access_method' in val:
                    unq.access_method = val['access_method']
                if 'description' in val:
                    unq.description = val['description']
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
            for (sch, tbl, cns) in self.keys():
                constr = self[(sch, tbl, cns)]
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
            for (sch, tbl, cns) in inconstrs.keys():
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
                    stmts.append(inconstr.add())
                else:
                    # check constraint objects
                    stmts.append(self[(sch, tbl, cns)].diff_map(inconstr))

        return stmts
