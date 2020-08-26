# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.index
    ~~~~~~~~~~~~~~~~~~~~~~

    This defines two classes, Index and IndexDict, derived
    from DbSchemaObject and DbObjectDict, respectively.
"""
from . import DbObjectDict, DbSchemaObject
from . import quote_id, commentable


def split_exprs(idx_exprs):
    "Helper function to split index expressions from pg_get_expr()"
    level = 0
    in_literal = False
    splits = []

    # Split around commas but only at the first parens level.
    # TODO: you can still fool this function with a string containing a quote.
    start = 0
    for i, c in enumerate(idx_exprs):
        if c == "'":
            in_literal = not in_literal
            continue
        if in_literal:
            continue
        elif c == '(':
            level += 1
        elif c == ')':
            level -= 1
        elif c == ',' and level == 0:
            splits.append((start, i))
            start = i + 1
            for s in idx_exprs[start:]:
                if s == ' ':
                    start += 1
                else:
                    break
    splits.append((start, i+1))
    return [idx_exprs[start:end] for start, end in splits]


class Index(DbSchemaObject):
    """A physical index definition, other than a primary key or unique
    constraint index.

    An index is identified by its schema name and index name.  However,
    at this time, Pyrseas uses the triple schema-table-index names as the
    identifier.
    """
    # TODO:  This should be fixed in this or a subsequent release.

    keylist = ['schema', 'table', 'name']
    catalog = 'pg_index'

    def __init__(self, name, schema, table, description, unique=False,
                 access_method='btree', keys=[], predicate=None,
                 tablespace=None, cluster=False, keyexprs=None, defn=None,
                 oid=None):
        """Initialize the index

        :param name: index name (from relname)
        :param schema: schema name (from nspname via relnamespace)
        :param table: table name (from indrelid)
        :param description: comment text (from obj_description)
        :param unique: unique indicator (from indisunique)
        :param access_method: access method (from amname via relam)
        :param keys: list of columns (from indkey)
        :param predicate: partial index predicate (from indpred)
        :param tablespace: tablespace name (from spcname via reltablespace)
        :param cluster: clustered indicator (from indisclustered)
        :param keyexprs: list of expressions (from indexprs)
        :param defn: index definition (from pg_get_indexdef)
        """
        super(Index, self).__init__(name, schema, description)
        self.table = self.unqualify(table)
        self.unique = unique
        self.access_method = access_method
        if defn is not None:
            self.keys = self._parse_keys(keys, keyexprs, defn)
        else:
            self.keys = keys
        self.predicate = predicate
        self.tablespace = tablespace
        self.cluster = cluster
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT nspname AS schema, indrelid::regclass AS table,
                   c.relname AS name, amname AS access_method,
                   indisunique AS unique, indkey AS keys,
                   pg_get_expr(indexprs, indrelid) AS keyexprs,
                   pg_get_expr(indpred, indrelid) AS predicate,
                   pg_get_indexdef(indexrelid) AS defn,
                   spcname AS tablespace, indisclustered AS cluster,
                   obj_description (c.oid, 'pg_class') AS description, c.oid
            FROM pg_index i JOIN pg_class c ON (indexrelid = c.oid)
                 JOIN pg_namespace ON (relnamespace = pg_namespace.oid)
                 JOIN pg_am ON (relam = pg_am.oid)
                 LEFT JOIN pg_tablespace t ON (c.reltablespace = t.oid)
            WHERE NOT indisprimary AND c.relpersistence != 't'
              AND (nspname != 'pg_catalog' AND nspname != 'information_schema')
              AND NOT EXISTS (
                     SELECT 1 FROM pg_constraint
                     WHERE contype in ('p', 'u')
                     AND conindid = c.oid)
           ORDER BY schema, "table", name"""

    @staticmethod
    def from_map(name, table, inobj):
        """Initialize an index instance from a YAML map

        :param name: index name
        :param table: map of table
        :param inobj: YAML map of the index
        :return: Index instance
        """
        keys = 'keys'
        if 'columns' in inobj:
            keys = 'columns'
        elif 'keys' not in inobj:
            raise KeyError("Index '%s' is missing keys specification" % name)
        obj = Index(
            name, table.schema, table.name, inobj.pop('description', None),
            inobj.pop('unique', False), inobj.pop('access_method', 'btree'),
            inobj.pop(keys, []), inobj.pop('predicate', None),
            inobj.pop('tablespace', None), inobj.pop('cluster', False))
        if 'depends_on' in inobj:
            obj.depends_on.extend(inobj['depends_on'])
        obj.set_oldname(inobj)
        return obj

    def _parse_keys(self, keycols, exprs, defn):
        keydefs, _, _ = defn.partition(' WHERE ')
        _, _, keydefs = keydefs.partition(' USING ')
        keydefs = keydefs[keydefs.find(' (') + 2:-1]
        # split expressions
        if exprs is not None:
            exprs = split_exprs(exprs)
        i = 0
        rest = keydefs
        keys = []
        for col in keycols.split():
            keyopts = []
            extra = {}
            if col == '0':
                expr = exprs[i]
                if rest and rest[0] == '(':
                    expr = '(' + expr + ')'
                assert(rest.startswith(expr))
                key = expr
                extra = {'type': 'expression'}
                explen = len(expr)
                loc = rest[explen:].find(',')
                if loc == 0:
                    keyopts = []
                    rest = rest[explen + 1:].lstrip()
                elif loc == -1:
                    keyopts = rest[explen:].split()
                    rest = ''
                else:
                    keyopts = rest[explen:explen + loc].split()
                    rest = rest[explen + loc + 1:].lstrip()
                i += 1
            else:
                loc = rest.find(',')
                key = rest[:loc] if loc != -1 else rest.lstrip()
                keyopts = key.split()[1:]
                key = key.split()[0]
                rest = rest[loc + 1:]
            rest = rest.lstrip()
            skipnext = False
            for j, opt in enumerate(keyopts):
                if skipnext:
                    skipnext = False
                    continue
                if opt.upper() not in ['COLLATE', 'ASC', 'DESC', 'NULLS',
                                       'FIRST', 'LAST']:
                    extra.update(opclass=opt)
                    continue
                elif opt == 'COLLATE':
                    extra.update(collation=keyopts[j + 1])
                    skipnext = True
                elif opt == 'NULLS':
                    extra.update(nulls=keyopts[j + 1].lower())
                    skipnext = True
                elif opt == 'DESC':
                    extra.update(order='desc')
            if extra:
                key = {key: extra}
            keys.append(key)
        return keys

    def key_expressions(self):
        """Return comma-separated list of key column names and qualifiers

        :return: string
        """
        colspec = []
        for col in self.keys:
            if isinstance(col, str):
                colspec.append(col)
            else:
                clause = list(col.keys())[0]
                vals = list(col.values())[0]
                if 'collation' in vals:
                    clause += ' COLLATE ' + vals['collation']
                if 'opclass' in vals:
                    clause += ' ' + vals['opclass']
                if 'order' in vals:
                    clause += ' ' + vals['order'].upper()
                if 'nulls' in vals:
                    clause += ' NULLS ' + vals['nulls'].upper()
                colspec.append(clause)
        return ", ".join(colspec)

    def to_map(self, db):
        """Convert an index definition to a YAML-suitable format

        :return: dictionary
        """
        dct = super(Index, self).to_map(db)
        if self.access_method == 'btree':
            dct.pop('access_method')
        if not self.unique:
            dct.pop('unique')
        for attr in ['predicate', 'tablespace']:
            if getattr(self, attr) is None:
                dct.pop(attr)
        if not self.cluster:
            dct.pop('cluster')
        return {self.name: dct}

    @commentable
    def create(self, dbversion=None):
        """Return a SQL statement to CREATE the index

        :return: SQL statements
        """
        stmts = []

        # indexes defined by constraints are not to be dealt with as indexes
        if getattr(self, '_for_constraint', None):
            return stmts

        acc = ''
        if self.access_method != 'btree':
            acc = 'USING %s ' % self.access_method
        tblspc = ''
        if self.tablespace is not None:
            tblspc = '\n    TABLESPACE %s' % self.tablespace
        pred = ''
        if self.predicate is not None:
            pred = '\n    WHERE %s' % self.predicate
        stmts.append("CREATE %sINDEX %s ON %s %s(%s)%s%s" % (
            'UNIQUE ' if self.unique else '', quote_id(self.name),
            self.qualname(self.schema, self.table), acc,
            self.key_expressions(), tblspc, pred))
        if self.cluster:
            stmts.append("CLUSTER %s USING %s" % (
                self.qualname(self.schema, self.table), quote_id(self.name)))
        return stmts

    def alter(self, inindex):
        """Generate SQL to transform an existing index

        :param inindex: a YAML map defining the new index
        :return: list of SQL statements

        Compares the index to an input index and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []

        # indexes defined by constraints are not to be dealt with as indexes
        if getattr(self, '_for_constraint', None):
            return stmts

        if self.access_method != inindex.access_method \
                or self.unique != inindex.unique \
                or self.keys != inindex.keys:
            stmts.append("DROP INDEX %s" % self.qualname())
            self.access_method = inindex.access_method
            self.unique = inindex.unique
            self.keys = inindex.keys
            stmts.append(self.create())

        base = "ALTER INDEX %s\n    " % self.qualname()
        if inindex.tablespace is not None:
            if self.tablespace is not None \
                    or self.tablespace != inindex.tablespace:
                stmts.append(base + "SET TABLESPACE %s"
                             % quote_id(inindex.tablespace))
        elif self.tablespace is not None:
            stmts.append(base + "SET TABLESPACE pg_default")
        if inindex.cluster:
            if not self.cluster:
                stmts.append("CLUSTER %s USING %s" % (
                    self.qualname(self.schema, self.table),
                    quote_id(self.name)))
        elif self.cluster:
            stmts.append("ALTER TABLE %s\n    SET WITHOUT CLUSTER" %
                         self.qualname(self.schema, self.table))
        stmts.append(super(Index, self).alter(inindex))
        return stmts

    def drop(self):
        """Generate SQL to drop the current index

        :return: list of SQL statements
        """
        # indexes defined by constraints are not to be dealt with as indexes
        if getattr(self, '_for_constraint', None):
            return []

        return ["DROP INDEX %s" % self.identifier()]

    def get_implied_deps(self, db):
        deps = super(Index, self).get_implied_deps(db)

        # add the table we are defined into
        deps.add(db.tables[self.schema, self.table])
        # TODO: add column collation specs if present

        return deps


class IndexDict(DbObjectDict):
    "The collection of indexes on tables in a database"

    cls = Index

    def _from_catalog(self):
        """Initialize the dictionary of indexes by querying the catalogs"""
        self.query = self.cls.query()
        for obj in self.fetch():
            self[obj.key()] = obj
            self.by_oid[obj.oid] = obj

    def from_map(self, table, inindexes):
        """Initialize the dictionary of indexes by converting the input map

        :param table: table owning the indexes
        :param inindexes: YAML map defining the indexes
        """
        for i in inindexes:
            inobj = inindexes[i]
            self[(table.schema, table.name, i)] = Index.from_map(
                i, table, inobj)
