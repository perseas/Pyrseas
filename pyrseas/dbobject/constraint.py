# -*- coding: utf-8 -*-
"""
    pyrseas.constraint
    ~~~~~~~~~~~~~~~~~~

    This module defines six classes: Constraint derived from
    DbSchemaObject, CheckConstraint, PrimaryKey, ForeignKey and
    UniqueConstraint derived from Constraint, and ConstraintDict
    derived from DbObjectDict.

    TODO: UniqueConstraint and PrimaryKey are nearly identical.
          Perhaps the latter should inherit from the former.
"""
from . import DbObjectDict, DbSchemaObject
from . import quote_id, split_schema_obj, commentable
from .index import Index


class Constraint(DbSchemaObject):
    """A constraint definition, such as a primary key, foreign key or
    unique constraint.  This also covers check constraints on domains."""

    keylist = ['schema', 'table', 'name']
    catalog = 'pg_constraint'

    def __init__(self, name, schema, table, description):
        """Initialize the constraint

        :param name: constraint name (from conname)
        :param schema: schema name (from connamespace)
        :param table: table/domain name (from conrelid/contypid)
        :param description: comment text (from obj_description())
        """
        super(Constraint, self).__init__(name, schema, description)
        self._init_own_privs(None, [])
        self.table = self.unqualify(table)

    def key_columns(self):
        """Return comma-separated list of key column names

        :return: string
        """
        return ", ".join([quote_id(col) for col in self.columns])

    def _normalize_columns(self):
        "Replace integer column numbers by column names"
        if isinstance(self.columns[0], int):
            self.columns = [self._table.columns[k - 1].name
                            for k in self.columns]

    def create(self, dbversion=None):
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
        if self.tablespace is not None:
            tblspc = " USING INDEX TABLESPACE %s" % self.tablespace
        stmts.append("ALTER TABLE %s ADD CONSTRAINT %s %s (%s)%s" % (
            self._table.qualname(), quote_id(self.name),
            self.objtype, self.key_columns(), tblspc))
        if self.cluster:
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
            raise KeyError("Constraint '%s.%s' on unknown type/class" % (
                self.schema, self.name))

        return deps


class CheckConstraint(Constraint):
    "A check constraint definition"

    def __init__(self, name, schema, table, description, columns,
                 expression, is_domain_check=False, inherited=False,
                 oid=None):
        """Initialize the check constraint

        :param name-description: see Constraint.__init__ params
        :param columns: list of columns (should only be one) (from conkey)
        :param expression: constraint expression (from consrc)
        :param is_domain_check: is constraint for a domain? (from contypid)
        :param inherited: is it inherited? (from coninhcount)
        """
        super(CheckConstraint, self).__init__(name, schema, table, description)
        self.columns = columns
        if expression[0] == '(':
            assert expression[-1] == ')'
        self.expression = expression
        self.is_domain_check = is_domain_check
        self.inherited = inherited
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return r"""
            SELECT conname AS name, nspname AS schema,
                   CASE WHEN contypid = 0 THEN conrelid::regclass::text
                        ELSE contypid::regtype::text END AS table,
                   contypid != 0 AS is_domain_check, conkey AS columns,
                   pg_get_expr(conbin, conrelid) AS expression,
                   coninhcount > 0 AS inherited, c.oid,
                   obj_description(c.oid, 'pg_constraint') AS description
            FROM pg_constraint c
                 JOIN pg_namespace ON (connamespace = pg_namespace.oid)
            WHERE nspname != 'pg_catalog' AND nspname != 'information_schema'
                  AND nspname NOT LIKE 'pg_temp\_%'
                  AND nspname NOT LIKE 'pg_toast_temp\_%'
              AND contype = 'c'
              AND contypid NOT IN (SELECT objid FROM pg_depend
                  WHERE deptype = 'e' AND classid = 'pg_type'::regclass)
            ORDER BY schema, "table", name"""

    @staticmethod
    def from_map(name, table, target, inobj):
        """Initialize a CheckConstraint instance from a YAML map

        :param name: constraint name
        :param table: table map
        :param target: column (default) or domain indicator
        :param inobj: YAML map of the constraint
        :return: CheckConstraint instance
        """
        obj = CheckConstraint(
            name, table.schema, table.name, inobj.pop('description', None),
            inobj.pop('columns', []), inobj.pop('expression', None),
            (target != ''), inobj.pop('inherited', False))
        if 'depends_on' in inobj:
            obj.depends_on.extend(inobj.pop('depends_on'))
        return obj

    @property
    def objtype(self):
        return "CHECK"

    def to_map(self, db, dbcols):
        """Convert a check constraint definition to a YAML-suitable format

        :param dbcols: dictionary of dbobject columns
        :return: dictionary
        """
        dct = super(CheckConstraint, self).to_map(db)
        dct.pop('is_domain_check')
        if not self.inherited:
            dct.pop('inherited')
        if dbcols is not None and self.columns is not None:
            dct['columns'] = [dbcols[k - 1] for k in self.columns]
        else:
            dct.pop('columns')
        return {self.name: dct}

    @commentable
    def add(self):
        """Return string to add the CHECK constraint via ALTER TABLE

        :return: SQL statement
        """
        # Don't generate inherited constraints
        if self.inherited:
            return []

        if self.expression[0] != '(':
            expr = "(%s)" % self.expression
        else:
            expr = self.expression
        return ["ALTER %s %s ADD CONSTRAINT %s %s %s" % (
            self._table.objtype, self._table.qualname(), quote_id(self.name),
            self.objtype, expr)]

    def drop(self):
        if self.inherited:
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
        if inchk.expression != self.expression:
            if inchk.expression.lower() != self.expression.lower():
                stmts.append(self.drop())
                stmts.append(inchk.add())
        stmts.append(self.diff_description(inchk))
        return stmts


class PrimaryKey(Constraint):
    "A primary key constraint definition"

    def __init__(self, name, schema, table, description, columns,
                 access_method='btree', tablespace=None, cluster=False,
                 inherited=False, deferrable=False, deferred=False,
                 oid=None):
        """Initialize the primary key

        :param name-description: see Constraint.__init__ params
        :param columns: list of columns (should only be one) (from conkey)
        :param access_method: index access method (from am_name via conindid)
        :param tablespace: storage tablespace (from spcname)
        :param cluster: is index clustered? (from indisclustered)
        :param inherited: is PK inherited? (from coninhcount)
        :param deferrable: is constraint deferrable? (from condeferrable)
        :param deferred: is constraint deferred? (from condeferred)
        """
        super(PrimaryKey, self).__init__(name, schema, table, description)
        self.columns = columns
        self.access_method = access_method
        self.tablespace = tablespace
        self.cluster = cluster
        self.inherited = inherited
        self.deferrable = deferrable
        self.deferred = deferred
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return r"""
            SELECT conname AS name, nspname AS schema,
                   conrelid::regclass AS table, conkey AS columns,
                   condeferrable AS deferrable, condeferred AS deferred,
                   amname AS access_method, spcname AS tablespace, c.oid,
                   indisclustered AS cluster, coninhcount > 0 AS inherited,
                   obj_description(c.oid, 'pg_constraint') AS description
            FROM pg_constraint c
                 JOIN pg_namespace ON (connamespace = pg_namespace.oid)
                 JOIN pg_index i ON (indexrelid = conindid)
                 JOIN pg_class cl on (indexrelid = cl.oid)
                 JOIN pg_am on (relam = pg_am.oid)
                 LEFT JOIN pg_tablespace t ON (cl.reltablespace = t.oid)
            WHERE nspname != 'pg_catalog' AND nspname != 'information_schema'
                  AND nspname NOT LIKE 'pg_temp\_%'
                  AND nspname NOT LIKE 'pg_toast_temp\_%'
              AND contype = 'p'
              AND contypid NOT IN (SELECT objid FROM pg_depend
                  WHERE deptype = 'e' AND classid = 'pg_type'::regclass)
              AND conrelid NOT IN (SELECT objid FROM pg_depend
                  WHERE deptype = 'e' AND classid = 'pg_class'::regclass)
            ORDER BY schema, "table", name"""

    @staticmethod
    def from_map(name, table, inobj):
        """Initialize a PrimaryKey instance from a YAML map

        :param name: key name
        :param table: table map
        :param inobj: YAML map of the primary key
        :return: PrimaryKey instance
        """
        return PrimaryKey(
            name, table.schema, table.name, inobj.pop('description', None),
            inobj.pop('columns', []), inobj.pop('access_method', 'btree'),
            inobj.pop('tablespace', None), inobj.pop('cluster', False),
            inobj.pop('inherited', False), inobj.pop('deferrable', False),
            inobj.pop('deferred', False))

    @property
    def objtype(self):
        return "PRIMARY KEY"

    def to_map(self, db, dbcols):
        """Convert a primary key definition to a YAML-suitable format

        :param dbcols: dictionary of dbobject columns
        :return: dictionary
        """
        dct = super(PrimaryKey, self).to_map(db)
        if self.access_method == 'btree':
            dct.pop('access_method')
        for attr in ('inherited', 'deferrable', 'deferred', 'cluster'):
            if getattr(self, attr) is False:
                dct.pop(attr)
        if self.tablespace is None:
            dct.pop('tablespace')
        if '_table' in dct:
            del dct['_table']
        dct['columns'] = [dbcols[k - 1] for k in self.columns]
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
        self._normalize_columns()
        if inpk.columns != self.columns:
            stmts.append(self.drop())
            stmts.append(inpk.add())
        if inpk.cluster:
            if not self.cluster:
                stmts.append("CLUSTER %s USING %s" % (
                    self._table.qualname(), quote_id(self.name)))
        elif self.cluster:
            stmts.append("ALTER TABLE %s\n    SET WITHOUT CLUSTER" %
                         self._table.qualname())
        stmts.append(self.diff_description(inpk))
        return stmts


ACTIONS = {'r': 'restrict', 'c': 'cascade', 'n': 'set null',
           'd': 'set default'}
MATCH_TYPES = {'f': 'full', 'p': 'partial', 's': 'simple'}


class ForeignKey(Constraint):
    "A foreign key constraint definition"

    def __init__(self, name, schema, table, description, columns,
                 ref_table, ref_cols, on_update, on_delete, match,
                 access_method='btree', tablespace=None, cluster=False,
                 inherited=False, deferrable=False, deferred=False,
                 oid=None):
        """Initialize the foreign key

        :param name-description: see Constraint.__init__ params
        :param columns: list of columns (should only be one) (from conkey)
        :param ref_table: referenced table (from confrelid)
        :param ref_cols: referenced columns (from confkey)
        :param on_update: update action code (from confupdtype)
        :param on_delete: delete action code (from confdeltype)
        :param match: match action code (from confmatchtype)
        :param access_method: index access method (from am_name via conindid)
        :param tablespace: storage tablespace (from spcname)
        :param cluster: is index clustered? (from indisclustered)
        :param inherited: is PK inherited? (from coninhcount)
        :param deferrable: is constraint deferrable? (from condeferrable)
        :param deferred: is constraint deferred? (from condeferred)
        """
        super(ForeignKey, self).__init__(name, schema, table, description)
        self.columns = columns
        (self.ref_schema, self.ref_table) = split_schema_obj(ref_table, schema)
        self.ref_cols = ref_cols
        if on_update is not None and len(on_update) == 1:
            self.on_update = None if on_update == 'a' else ACTIONS[on_update]
        else:
            assert on_update is None or on_update in ACTIONS.values()
            self.on_update = on_update
        if on_delete is not None and len(on_delete) == 1:
            self.on_delete = None if on_delete == 'a' else ACTIONS[on_delete]
        else:
            assert on_delete is None or on_delete in ACTIONS.values()
            self.on_delete = on_delete
        if match is not None and len(match) == 1:
            self.match = MATCH_TYPES[match]
        else:
            assert match is None or match in MATCH_TYPES.values()
            self.match = 'simple' if match is None else match
        self.access_method = access_method
        self.tablespace = tablespace
        self.cluster = cluster
        self.inherited = inherited
        self.deferrable = deferrable
        self.deferred = deferred
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return r"""
            SELECT conname AS name, nspname AS schema,
                   conrelid::regclass AS table, conkey AS columns,
                   condeferrable AS deferrable, condeferred AS deferred,
                   confrelid::regclass AS ref_table, confkey AS ref_cols,
                   confupdtype AS on_update, confdeltype AS on_delete,
                   confmatchtype AS match, amname AS access_method,
                   spcname AS tablespace, c.oid,
                   indisclustered AS cluster, coninhcount > 0 AS inherited,
                   obj_description(c.oid, 'pg_constraint') AS description
            FROM pg_constraint c
                 JOIN pg_namespace ON (connamespace = pg_namespace.oid)
                 JOIN pg_index i ON (indexrelid = conindid)
                 JOIN pg_class cl ON (indexrelid = cl.oid)
                 JOIN pg_am on (relam = pg_am.oid)
                 LEFT JOIN pg_tablespace t ON (cl.reltablespace = t.oid)
            WHERE nspname != 'pg_catalog' AND nspname != 'information_schema'
                  AND nspname NOT LIKE 'pg_temp\_%'
                  AND nspname NOT LIKE 'pg_toast_temp\_%'
              AND contype = 'f'
              AND contypid NOT IN (SELECT objid FROM pg_depend
                  WHERE deptype = 'e' AND classid = 'pg_type'::regclass)
              AND conrelid NOT IN (SELECT objid FROM pg_depend
                  WHERE deptype = 'e' AND classid = 'pg_class'::regclass)
            ORDER BY schema, "table", name"""

    @staticmethod
    def from_map(name, table, inobj):
        """Initialize a ForeignKey instance from a YAML map

        :param name: key name
        :param table: table map
        :param inobj: YAML map of the foreign key
        :return: ForeignKey instance
        """
        if 'references' not in inobj:
            raise KeyError("Constraint '%s' missing references" % name)
        refs = inobj['references']
        if 'table' not in refs:
            raise KeyError("Constraint '%s' missing table reference" % name)
        ref_table = refs['table']
        if 'schema' in refs and refs['schema'] != table.schema:
            ref_table = "%s.%s" % (refs['schema'], ref_table)
        if 'columns' not in refs:
            raise KeyError("Constraint '%s' missing reference columns" % name)
        obj = ForeignKey(
            name, table.schema, table.name, inobj.pop('description', None),
            inobj.pop('columns', []), ref_table, refs['columns'],
            inobj.pop('on_update', None), inobj.pop('on_delete', None),
            inobj.pop('match', None), inobj.pop('access_method', 'btree'),
            inobj.pop('tablespace', None), inobj.pop('cluster', False),
            inobj.pop('inherited', False), inobj.pop('deferrable', False),
            inobj.pop('deferred', False))
        obj.depends_on.extend(inobj.get('depends_on', ()))
        return obj

    @property
    def objtype(self):
        return "FOREIGN KEY"

    def _normalize_columns(self):
        "Replace integer column numbers by column names"
        super(ForeignKey, self)._normalize_columns()
        if isinstance(self.ref_cols[0], int):
            self.ref_cols = [self._references.columns[k - 1].name
                             for k in self.ref_cols]

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
        self._normalize_columns()
        dct = super(ForeignKey, self).to_map(db)
        if '_table' in dct:
            del dct['_table']
        if self.access_method == 'btree':
            dct.pop('access_method')
        for attr in ('inherited', 'deferrable', 'deferred', 'cluster'):
            if getattr(self, attr) is False:
                dct.pop(attr)
        for attr in ('tablespace', 'on_update', 'on_delete'):
            if getattr(self, attr) is None:
                dct.pop(attr)
        if self.match == 'simple':
            dct.pop('match')
        dct['references'] = {'table': dct['ref_table'],
                             'columns': self.ref_cols}
        if 'ref_schema' in dct:
            dct['references'].update(schema=self.ref_schema)
            dct.pop('ref_schema')
        dct.pop('ref_table')
        dct.pop('ref_cols')

        return {self.name: dct}

    @commentable
    def add(self):
        """Return string to add the foreign key via ALTER TABLE

        :return: SQL statement
        """
        match = ''
        if self.match is not None and self.match != 'simple':
            match = " MATCH %s" % self.match.upper()
        actions = ''
        if self.on_update is not None:
            actions = " ON UPDATE %s" % self.on_update.upper()
        if self.on_delete is not None:
            actions += " ON DELETE %s" % self.on_delete.upper()
        if self.deferrable:
            actions += " DEFERRABLE"
        if self.deferred:
            actions += " INITIALLY DEFERRED"

        return "ALTER TABLE %s ADD CONSTRAINT %s FOREIGN KEY (%s) " \
            "REFERENCES %s (%s)%s%s" % (
                self._table.qualname(), quote_id(self.name),
                self.key_columns(), self._references.qualname(),
                self.ref_columns(), match, actions)

    def alter(self, infk):
        """Generate SQL to transform an existing foreign key

        :param infk: a YAML map defining the new foreign key
        :return: list of SQL statements

        Compares the foreign key to an input foreign key and generates
        SQL statements to transform it into the one represented by the
        input.
        """
        stmts = []
        self._normalize_columns()
        if infk.columns != self.columns or infk.ref_cols != self.ref_cols \
           or infk.match != self.match or infk.on_update != self.on_update \
                or infk.on_delete != self.on_delete:
            stmts.append(self.drop())
            stmts.append(infk.add())
        stmts.append(self.diff_description(infk))
        return stmts

    def get_implied_deps(self, db):
        deps = super(ForeignKey, self).get_implied_deps(db)

        # add the table we reference
        deps.add(self._references)

        # A fkey needs a pkey, unique constraint or complete unique index
        # defined on the fields it references to be restored.
        idx = self._find_referenced_index(db, self._references)
        if idx:
            deps.add(idx)

        return deps

    def _find_referenced_index(self, db, ref_table):
        pkey = ref_table.primary_key
        if pkey is not None and pkey.columns == self.ref_cols:
            return pkey

        for uc in list(ref_table.unique_constraints.values()):
            uc._normalize_columns()
            if uc.columns == self.ref_cols:
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

    def __init__(self, name, schema, table, description, columns,
                 access_method='btree', tablespace=None, cluster=False,
                 inherited=False, deferrable=False, deferred=False,
                 oid=None):
        """Initialize the unique constraint

        :param name-description: see Constraint.__init__ params
        :param columns: list of columns (should only be one) (from conkey)
        :param access_method: index access method (from am_name via conindid)
        :param tablespace: storage tablespace (from spcname)
        :param cluster: is index clustered? (from indisclustered)
        :param inherited: is it inherited? (from coninhcount)
        :param deferrable: is constraint deferrable? (from condeferrable)
        :param deferred: is constraint deferred? (from condeferred)
        """
        super(UniqueConstraint, self).__init__(
            name, schema, table, description)
        self.columns = columns
        self.access_method = access_method
        self.tablespace = tablespace
        self.cluster = cluster
        self.inherited = inherited
        self.deferrable = deferrable
        self.deferred = deferred
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return r"""
            SELECT conname AS name, nspname AS schema,
                   conrelid::regclass AS table, conkey AS columns,
                   condeferrable AS deferrable, condeferred AS deferred,
                   amname AS access_method, spcname AS tablespace, c.oid,
                   indisclustered AS cluster, coninhcount > 0 AS inherited,
                   obj_description(c.oid, 'pg_constraint') AS description
            FROM pg_constraint c
                 JOIN pg_namespace ON (connamespace = pg_namespace.oid)
                 JOIN pg_index i ON (indexrelid = conindid)
                 JOIN pg_class cl on (indexrelid = cl.oid)
                 JOIN pg_am on (relam = pg_am.oid)
                 LEFT JOIN pg_tablespace t ON (cl.reltablespace = t.oid)
            WHERE nspname != 'pg_catalog' AND nspname != 'information_schema'
                  AND nspname NOT LIKE 'pg_temp\_%'
                  AND nspname NOT LIKE 'pg_toast_temp\_%'
              AND contype = 'u'
              AND contypid NOT IN (SELECT objid FROM pg_depend
                  WHERE deptype = 'e' AND classid = 'pg_type'::regclass)
              AND conrelid NOT IN (SELECT objid FROM pg_depend
                  WHERE deptype = 'e' AND classid = 'pg_class'::regclass)
            ORDER BY schema, "table", name"""

    @staticmethod
    def from_map(name, table, inobj):
        """Initialize a UniqueConstraint instance from a YAML map

        :param name: constraint name
        :param table: table map
        :param inobj: YAML map of the constraint
        :return: UniqueConstraint instance
        """
        return UniqueConstraint(
            name, table.schema, table.name, inobj.pop('description', None),
            inobj.pop('columns', []), inobj.pop('access_method', 'btree'),
            inobj.pop('tablespace', None), inobj.pop('cluster', False),
            inobj.pop('inherited', False), inobj.pop('deferrable', False),
            inobj.pop('deferred', False))

    @property
    def objtype(self):
        return "UNIQUE"

    def to_map(self, db, dbcols):
        """Convert a unique constraint definition to a YAML-suitable format

        :param dbcols: dictionary of dbobject columns
        :return: dictionary
        """
        self._normalize_columns()
        dct = super(UniqueConstraint, self).to_map(db)
        if self.access_method == 'btree':
            dct.pop('access_method')
        for attr in ('inherited', 'deferrable', 'deferred', 'cluster'):
            if getattr(self, attr) is False:
                dct.pop(attr)
        if self.tablespace is None:
            dct.pop('tablespace')
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
        self._normalize_columns()
        if inuc.columns != self.columns:
            stmts.append(self.drop())
            stmts.append(inuc.add())
        if inuc.cluster:
            if not self.cluster:
                stmts.append("CLUSTER %s USING %s" % (
                    self._table.qualname(), quote_id(self.name)))
        elif self.cluster:
            stmts.append("ALTER TABLE %s\n    SET WITHOUT CLUSTER" %
                         self._table.qualname())
        stmts.append(self.diff_description(inuc))
        return stmts


MATCHTYPES_PRE93 = {'f': 'full', 'p': 'partial', 'u': 'simple'}


class ConstraintDict(DbObjectDict):
    "The collection of table or column constraints in a database"

    cls = Constraint

    def _from_catalog(self):
        """Initialize the dictionary of constraints by querying the catalogs"""
        for cls in (CheckConstraint, PrimaryKey, ForeignKey,
                    UniqueConstraint):
            self.cls = cls
            for obj in self.fetch():
                self[obj.key()] = obj
                self.by_oid[obj.oid] = obj

    def from_map(self, table, inconstrs, target=''):
        """Initialize the dictionary of constraints by converting the input map

        :param table: table affected by the constraints
        :param inconstrs: YAML map defining the constraints
        :param target: column or domain indicator
        """
        if 'check_constraints' in inconstrs:
            chks = inconstrs['check_constraints']
            for cns in chks:
                inobj = chks[cns]
                self[(table.schema, table.name, cns)] = \
                    CheckConstraint.from_map(cns, table, target, inobj)
        if 'primary_key' in inconstrs:
            cns = list(inconstrs['primary_key'].keys())[0]
            inobj = inconstrs['primary_key'][cns]
            self[(table.schema, table.name, cns)] = PrimaryKey.from_map(
                cns, table, inobj)
        if 'foreign_keys' in inconstrs:
            fkeys = inconstrs['foreign_keys']
            for cns in fkeys:
                inobj = fkeys[cns]
                self[(table.schema, table.name, cns)] = ForeignKey.from_map(
                    cns, table, inobj)
        if 'unique_constraints' in inconstrs:
            uconstrs = inconstrs['unique_constraints']
            for cns in uconstrs:
                inobj = uconstrs[cns]
                self[(table.schema, table.name, cns)] = \
                    UniqueConstraint.from_map(cns, table, inobj)

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
