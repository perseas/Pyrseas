# -*- coding: utf-8 -*-
"""
    pyrseas.constraint
    ~~~~~~~~~~~~~~~~~~

    This module defines six classes: Constraint derived from
    DbSchemaObject, CheckConstraint, PrimaryKey, ForeignKey and
    UniqueConstraint derived from Constraint, and ConstraintDict
    derived from DbObjectDict.
"""
import re

from pyrseas.dbobject import DbObjectDict, DbSchemaObject
from pyrseas.dbobject import quote_id, split_schema_obj, commentable
from pyrseas.dbobject.index import Index


ACTIONS = {'r': 'restrict', 'c': 'cascade', 'n': 'set null',
           'd': 'set default'}


class Constraint(DbSchemaObject):
    """A constraint definition, such as a primary key, foreign key or
       unique constraint"""

    keylist = ['schema', 'table', 'name']
    catalog = 'pg_constraint'

    def key_columns(self):
        """Return comma-separated list of key column names

        :return: string
        """
        return ", ".join([quote_id(col) for col in self.keycols])

    def create(self):
        # TODO: is add really needed?
        return self.add()

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
        return ["ALTER %s %s DROP CONSTRAINT %s" % (
            self._table.objtype, self._table.qualname(), quote_id(self.name))]

    def comment(self):
        """Return SQL statement to create COMMENT on constraint

        :return: SQL statement
        """
        return "COMMENT ON CONSTRAINT %s ON %s IS %s" % (
            quote_id(self.name), self._table.qualname(), self._comment_text())

    def get_implied_deps(self, db):
        from .table import Table
        from .dbtype import Domain
        deps = super(Constraint, self).get_implied_deps(db)

        if isinstance(self._table, Table):
            deps.add(db.tables[self.schema, self.table])
        elif isinstance(self._table, Domain):
            deps.add(db.types[self.schema, self.table])
        else:
            raise KeyError("Constraint '%s' on unknown type/class" % (
                quote_id(self.schema, self.name)))

        return deps


class CheckConstraint(Constraint):
    "A check constraint definition"

    @property
    def objtype(self):
        return "CHECK"

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
        # Don't generate inherited constraints
        if getattr(self, 'inherited', None):
            return []

        return ["ALTER %s %s ADD CONSTRAINT %s %s (%s)" % (
            self._table.objtype, self._table.qualname(), quote_id(self.name),
            self.objtype, self.expression)]

    def drop(self):
        if getattr(self, 'inherited', None):
            return []
        else:
            return super(CheckConstraint, self).drop()

    def alter(self, inchk):
        """Generate SQL to transform an existing CHECK constraint

        :param inchk: a YAML map defining the new CHECK constraint
        :return: list of SQL statements

        Compares the CHECK constraint to an input constraint and generates
        SQL statements to transform it into the one represented by the
        input.
        """
        stmts = []
        if hasattr(inchk, 'expression') and hasattr(self, 'expression'):
            if re.sub('[\s()]', '', inchk.expression.lower()) != \
               re.sub('[\s()]', '', self.expression.lower()):
                stmts.append(
                    "ALTER TABLE {tname} DROP CONSTRAINT {conname}".format(
                        tname=inchk._table.name, conname=inchk.name))
                stmts.append("ALTER TABLE {tname} ADD CONSTRAINT {conname}"
                             " CHECK ({exp})".format(
                                 tname=inchk._table.name, conname=inchk.name,
                                 exp=inchk.expression))
        stmts.append(self.diff_description(inchk))
        return stmts


class PrimaryKey(Constraint):
    "A primary key constraint definition"

    @property
    def objtype(self):
        return "PRIMARY KEY"

    def to_map(self, db, dbcols):
        """Convert a primary key definition to a YAML-suitable format

        :param dbcols: dictionary of dbobject columns
        :return: dictionary
        """
        dct = self._base_map(db)
        if dct['access_method'] == 'btree':
            del dct['access_method']
        if '_table' in dct:
            del dct['_table']
        dct['columns'] = [dbcols[k - 1] for k in self.keycols]
        del dct['keycols']
        return {self.name: dct}

    def alter(self, inpk):
        """Generate SQL to transform an existing primary key

        :param inpk: a YAML map defining the new primary key
        :return: list of SQL statements

        Compares the primary key to an input primary key and generates
        SQL statements to transform it into the one represented by the
        input.
        """
        stmts = []
        if hasattr(inpk, 'keycols') and hasattr(self, 'keycols') \
           and hasattr(self, '_table') and hasattr(self._table, 'columns') \
           and hasattr(self._table, 'primary_key') and \
           hasattr(self._table.primary_key, 'keycols'):
            selfcols = {i.number: i.name for i in self._table.columns}
            selfpk = [selfcols[i] for i in self._table.primary_key.keycols]
            if inpk.keycols != selfpk:
                stmts.append(
                    "ALTER TABLE {tname} DROP CONSTRAINT {pkname}".format(
                        tname=self._table.name, pkname=self.name))
                stmts.append("ALTER TABLE {tname} ADD CONSTRAINT {pkname} "
                             "PRIMARY KEY ({cols})".format(
                                 tname=inpk._table.name, pkname=inpk.name,
                                 cols=', '.join(inpk.keycols)))
        if hasattr(inpk, 'cluster'):
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

    @property
    def objtype(self):
        return "FOREIGN KEY"

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
        if '_table' in dct:
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
                self._table.qualname(), quote_id(self.name),
                self.key_columns(), self.references.qualname(),
                self.ref_columns(), match, actions)

    def get_match_actions(self):
        match = ""
        actions = ""
        if hasattr(self, 'match'):
            match = " MATCH %s" % self.match.upper()
        if hasattr(self, 'on_update'):
            actions = " ON UPDATE %s" % self.on_update.upper()
        if hasattr(self, 'on_delete'):
            actions += " ON DELETE %s" % self.on_delete.upper()
        if getattr(self, 'deferrable', False):
            actions += " DEFERRABLE"
        if getattr(self, 'deferred', False):
            actions += " INITIALLY DEFERRED"
        return {'match': match, 'actions': actions}

    def alter(self, infk):
        """Generate SQL to transform an existing foreign key

        :param infk: a YAML map defining the new foreign key
        :return: list of SQL statements

        Compares the foreign key to an input foreign key and generates
        SQL statements to transform it into the one represented by the
        input.
        """
        stmts = []
        if hasattr(infk, 'keycols') and hasattr(self, 'keycols') \
           and hasattr(self, '_table') and hasattr(self._table, 'columns') \
           and hasattr(self, 'references') \
           and hasattr(self.references, 'columns'):
            selfcols = {i.number: i.name for i in self._table.columns}
            selffk = [selfcols[i] for i in self.keycols]
            selfrefs = {i.number: i.name for i in self.references.columns}
            selffkref = [selfrefs[i] for i in self.ref_cols]

            if infk.keycols != selffk or infk.ref_cols != selffkref \
                    or infk.get_match_actions()['match'] \
                    != self.get_match_actions()['match'] \
                    or infk.get_match_actions()['actions'] \
                    != self.get_match_actions()['actions']:
                stmts.append(
                    "ALTER TABLE {tname} DROP CONSTRAINT {fkname}".format(
                        tname=self._table.name, fkname=self.name))
                stmts.append("ALTER TABLE {tname} ADD CONSTRAINT {fkname} "
                             "FOREIGN KEY ({cols}) REFERENCES {rtname} "
                             "({rcols}){match}{actions}".format(
                                 tname=infk._table.name, fkname=infk.name,
                                 cols=', '.join(infk.keycols),
                                 rtname=infk.ref_table,
                                 rcols=', '.join(infk.ref_cols),
                                 match=infk.get_match_actions()['match'],
                                 actions=infk.get_match_actions()['actions']))
        stmts.append(self.diff_description(infk))
        return stmts

    def get_implied_deps(self, db):
        deps = super(ForeignKey, self).get_implied_deps(db)

        # add the table we reference
        deps.add(self.references)

        # A fkey needs a pkey, unique constraint or complete unique index
        # defined on the fields it references to be restored.
        idx = self._find_referenced_index(db, self.references)
        if idx:
            deps.add(idx)

        return deps

    def _find_referenced_index(self, db, ref_table):
        pkey = getattr(ref_table, 'primary_key', None)
        if pkey:
            if (hasattr(pkey, 'keycols') and pkey.keycols == self.ref_cols) \
               or (hasattr(pkey, 'col_names') and
                   pkey.col_names == self.ref_cols):
                return pkey

        if hasattr(ref_table, 'unique_constraints'):
            for uc in list(ref_table.unique_constraints.values()):
                if uc.keycols == self.ref_cols:
                    return uc

        if hasattr(ref_table, 'indexes'):
            if isinstance(self.ref_cols[0], int):
                col_names = [ref_table.columns[i-1].name
                             for i in self.ref_cols]
            else:
                col_names = self.ref_cols

            for idx in list(ref_table.indexes.values()):
                if getattr(idx, 'unique', False) \
                   and not getattr(idx, 'predicate', None) \
                   and idx.keys == col_names:
                    return idx


class UniqueConstraint(Constraint):
    "A unique constraint definition"

    @property
    def objtype(self):
        return "UNIQUE"

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

    def alter(self, inuc):
        """Generate SQL to transform an existing unique constraint

        :param inuc: a YAML map defining the new unique constraint
        :return: list of SQL statements

        Compares the unique constraint to an input unique constraint
        and generates SQL statements to transform it into the one
        represented by the input.
        """
        stmts = []
        if hasattr(inuc, 'keycols') and hasattr(self, 'keycols') \
           and hasattr(self, '_table') and hasattr(self._table, 'columns'):
            selfcols = {i.number: i.name for i in self._table.columns}
            selfunique = [selfcols[i] for i in self.keycols]
            if inuc.keycols != selfunique:
                stmts.append(
                    "ALTER TABLE {tname} DROP CONSTRAINT {conname}".format(
                        tname=self._table.name, conname=self.name))
                stmts.append("ALTER TABLE {tname} ADD CONSTRAINT {conname} "
                             "UNIQUE ({cols})".format(
                                 tname=inuc._table.name, conname=inuc.name,
                                 cols=', '.join(inuc.keycols)))
        if hasattr(inuc, 'cluster'):
            if not hasattr(self, 'cluster'):
                stmts.append("CLUSTER %s USING %s" % (
                    self._table.qualname(), quote_id(self.name)))
        elif hasattr(self, 'cluster'):
            stmts.append("ALTER TABLE %s\n    SET WITHOUT CLUSTER" %
                         self._table.qualname())
        stmts.append(self.diff_description(inuc))
        return stmts

MATCHTYPES_PRE93 = {'f': 'full', 'p': 'partial', 'u': 'simple'}
COMMON_ATTRS = ['access_method', 'tablespace', 'description', 'cluster',
                'depends_on']


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
                  coninhcount > 0 AS inherited,
                  obj_description(c.oid, 'pg_constraint') AS description
           FROM pg_constraint c
                JOIN pg_namespace ON (connamespace = pg_namespace.oid)
                LEFT JOIN pg_class cl on (conname = relname)
                LEFT JOIN pg_index i ON (i.indexrelid = cl.oid)
                LEFT JOIN pg_tablespace t ON (cl.reltablespace = t.oid)
                LEFT JOIN pg_am on (relam = pg_am.oid)
           WHERE nspname != 'pg_catalog' AND nspname != 'information_schema'
                 AND nspname NOT LIKE 'pg_temp\_%'
                 AND nspname NOT LIKE 'pg_toast_temp\_%'
             AND contypid NOT IN (SELECT objid FROM pg_depend
                                   WHERE deptype = 'e'
                                     AND classid = 'pg_type'::regclass)
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
            sch, tbl = split_schema_obj(quote_id(sch, tbl))     # TODO why?
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
                self.by_oid[oid] = self[(sch, tbl, cns)] \
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
                check.depends_on.extend(val.get('depends_on', ()))
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
                pkey.keycols = val['columns']
            except KeyError as exc:
                exc.args = ("Constraint '%s' is missing columns" % cns,)
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
                    exc.args = ("Constraint '%s' is missing columns" % cns,)
                    raise
                try:
                    refs = val['references']
                except KeyError as exc:
                    exc.args = ("Constraint '%s' missing references" % cns,)
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
                                % cns,)
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

    def link_refs(self, db):
        for c in list(self.values()):
            if isinstance(c, ForeignKey):
                # The constraint depends on an index. Which one is accidental:
                # it depends e.g. on which suitable index was available when
                # the constraint was defined. So here we drop the dependency
                # on the introspected one, while in get_implied_deps we give
                # our best shot to suggest one to depend on. This way we don't
                # need expliciting the dependency in yaml.
                c.depends_on = [obj for obj in c.depends_on
                                if not isinstance(obj, Index)]

            if isinstance(c, (PrimaryKey, UniqueConstraint)):
                # The constraint creates implicitly an index, so it depends on
                # any extra dependencies the index has. These may include e.g.
                # an operator class for a non-builtin type.
                idx = db.indexes.get((c.schema, c.table, c.name))
                if idx:
                    c.depends_on.extend(idx.depends_on)
