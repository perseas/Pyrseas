# -*- coding: utf-8 -*-
"""
    pyrseas.index
    ~~~~~~~~~~~~~

    This defines two classes, Index and IndexDict, derived
    from DbSchemaObject and DbObjectDict, respectively.
"""
from pyrseas.dbobject import DbObjectDict, DbSchemaObject
from pyrseas.dbobject import quote_id, split_schema_obj, commentable


def split_exprs(idx_exprs):
    "Helper function to split index expressions from pg_get_expr()"
    keyexprs = []
    nopen = nclose = beg = curr = 0
    for c in idx_exprs:
        curr += 1
        if c == '(':
            nopen += 1
        elif c == ')':
            nclose += 1
            if nopen > 0 and nopen == nclose:
                if idx_exprs[beg] == ',':
                    beg += 1
                if idx_exprs[beg] == ' ':
                    beg += 1
                keyexprs.append(idx_exprs[beg:curr])
                beg = curr
                nopen = nclose = 0
    return keyexprs


class Index(DbSchemaObject):
    """A physical index definition, other than a primary key or unique
    constraint index.
    """

    keylist = ['schema', 'table', 'name']
    objtype = "INDEX"

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

    def to_map(self):
        """Convert an index definition to a YAML-suitable format

        :return: dictionary
        """
        dct = self._base_map()
        if dct['access_method'] == 'btree':
            del dct['access_method']
        return {self.name: dct}

    @commentable
    def create(self):
        """Return a SQL statement to CREATE the index

        :return: SQL statements
        """
        stmts = []
        pth = self.set_search_path()
        if pth:
            stmts.append(pth)
        unq = hasattr(self, 'unique') and self.unique
        acc = ''
        if hasattr(self, 'access_method') and self.access_method != 'btree':
            acc = 'USING %s ' % self.access_method
        tblspc = ''
        if hasattr(self, 'tablespace'):
            tblspc = '\n    TABLESPACE %s' % self.tablespace
        stmts.append("CREATE %sINDEX %s ON %s %s(%s)%s" % (
            'UNIQUE ' if unq else '', quote_id(self.name),
            quote_id(self.table), acc, self.key_expressions(), tblspc))
        return stmts

    def diff_map(self, inindex):
        """Generate SQL to transform an existing index

        :param inindex: a YAML map defining the new index
        :return: list of SQL statements

        Compares the index to an input index and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []
        if not hasattr(self, 'unique'):
            self.unique = False
        if self.access_method != inindex.access_method \
                or self.unique != inindex.unique:
            stmts.append("DROP INDEX %s" % self.qualname())
            self.access_method = inindex.access_method
            self.unique = inindex.unique
            stmts.append(self.create())
        # TODO: need to deal with changes in keycols

        base = "ALTER INDEX %s\n    " % self.qualname()
        if hasattr(inindex, 'tablespace'):
            if not hasattr(self, 'tablespace') \
                    or self.tablespace != inindex.tablespace:
                stmts.append(base + "SET TABLESPACE %s"
                             % quote_id(inindex.tablespace))
        elif hasattr(self, 'tablespace'):
            stmts.append(base + "SET TABLESPACE pg_default")
        stmts.append(self.diff_description(inindex))
        return stmts


class IndexDict(DbObjectDict):
    "The collection of indexes on tables in a database"

    cls = Index
    query = \
        """SELECT nspname AS schema, indrelid::regclass AS table,
                  c.relname AS name, amname AS access_method,
                  indisunique AS unique, indkey AS keycols,
                  pg_get_expr(indexprs, indrelid) AS keyexprs,
                  pg_get_indexdef(indexrelid) AS defn,
                  spcname AS tablespace,
                  obj_description (c.oid, 'pg_class') AS description
           FROM pg_index JOIN pg_class c ON (indexrelid = c.oid)
                JOIN pg_namespace ON (relnamespace = pg_namespace.oid)
                JOIN pg_am ON (relam = pg_am.oid)
                LEFT JOIN pg_tablespace t ON (c.reltablespace = t.oid)
           WHERE NOT indisprimary
                 AND (nspname != 'pg_catalog'
                      AND nspname != 'information_schema')
                 AND c.relname NOT IN (
                     SELECT conname FROM pg_constraint
                     WHERE contype = 'u')
           ORDER BY schema, 2, name"""

    def _from_catalog(self):
        """Initialize the dictionary of indexes by querying the catalogs"""
        for index in self.fetch():
            index.unqualify()
            sch, tbl, idx = index.key()
            sch, tbl = split_schema_obj('%s.%s' % (sch, tbl))
            keydefs = index.defn[index.defn.find(' USING ') + 7:]
            keydefs = keydefs[keydefs.find(' (') + 2:-1]
            # split expressions (result of pg_get_expr)
            if hasattr(index, 'keyexprs'):
                keyexprs = split_exprs(index.keyexprs)
                del index.keyexprs
            # parse the keys
            i = 0
            rest = keydefs
            index.keys = []
            for col in index.keycols.split():
                keyopts = []
                extra = {}
                if col == '0':
                    expr = keyexprs[i]
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
                index.keys.append(key)
            del index.defn, index.keycols
            self[(sch, tbl, idx)] = index

    def from_map(self, table, inindexes):
        """Initialize the dictionary of indexes by converting the input map

        :param table: table owning the indexes
        :param inindexes: YAML map defining the indexes
        """
        for i in list(inindexes.keys()):
            idx = Index(schema=table.schema, table=table.name, name=i)
            val = inindexes[i]
            if 'keys' in val:
                idx.keys = val['keys']
            elif 'columns' in val:
                idx.keys = val['columns']
            else:
                raise KeyError("Index '%s' is missing keys specification" % i)
            for attr in ['access_method', 'unique', 'tablespace']:
                if attr in val:
                    setattr(idx, attr, val[attr])
            if not hasattr(idx, 'access_method'):
                idx.access_method = 'btree'
            if not hasattr(idx, 'unique'):
                idx.unique = False
            if 'description' in val:
                idx.description = val['description']
            if 'oldname' in val:
                idx.oldname = val['oldname']
            self[(table.schema, table.name, i)] = idx

    def diff_map(self, inindexes):
        """Generate SQL to transform existing indexes

        :param inindexes: a YAML map defining the new indexes
        :return: list of SQL statements

        Compares the existing index definitions, as fetched from the
        catalogs, to the input map and generates SQL statements to
        transform the indexes accordingly.
        """
        stmts = []
        # check input indexes
        for (sch, tbl, idx) in list(inindexes.keys()):
            inidx = inindexes[(sch, tbl, idx)]
            # does it exist in the database?
            if (sch, tbl, idx) not in self:
                # check for possible RENAME
                if hasattr(inidx, 'oldname'):
                    oldname = inidx.oldname
                    try:
                        stmts.append(self[(sch, tbl, oldname)].rename(
                                inidx.name))
                        del self[(sch, tbl, oldname)]
                    except KeyError as exc:
                        exc.args = ("Previous name '%s' for index '%s' "
                                  "not found" % (oldname, inidx.name), )
                        raise
                else:
                    # create new index
                    stmts.append(inidx.create())

        # check database indexes
        for (sch, tbl, idx) in list(self.keys()):
            index = self[(sch, tbl, idx)]
            # if missing, drop it
            if (sch, tbl, idx) not in inindexes:
                stmts.append(index.drop())
            else:
                # compare index objects
                stmts.append(index.diff_map(inindexes[(sch, tbl, idx)]))

        return stmts
