# -*- coding: utf-8 -*-
"""
    pyrseas.index
    ~~~~~~~~~~~~~

    This defines two classes, Index and IndexDict, derived
    from DbSchemaObject and DbObjectDict, respectively.
"""
from pyrseas.dbobject import DbObjectDict, DbSchemaObject
from pyrseas.dbobject import quote_id, split_schema_obj


class Index(DbSchemaObject):
    """A physical index definition, other than a primary key or unique
    constraint index.
    """

    keylist = ['schema', 'table', 'name']
    objtype = "INDEX"

    def key_columns(self):
        """Return comma-separated list of key column names and qualifiers

        :return: string
        """
        colspec = []
        for col in self.columns:
            if isinstance(col, str):
                colspec.append(col)
            else:
                clause = list(col.keys())[0]
                vals = list(col.values())[0]
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
        return {self.name: dct}

    def create(self):
        """Return a SQL statement to CREATE the index

        :return: SQL statements
        """
        stmts = []
        pth = self.set_search_path()
        if pth:
            stmts.append(pth)
        unq = hasattr(self, 'unique') and self.unique
        acc = hasattr(self, 'access_method') \
            and 'USING %s ' % self.access_method or ''
        stmts.append("CREATE %sINDEX %s ON %s %s(%s)" % (
            unq and 'UNIQUE ' or '', quote_id(self.name), quote_id(self.table),
            acc, hasattr(self, 'columns') and self.key_columns() or
            self.expression))
        if hasattr(self, 'description'):
            stmts.append(self.comment())
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
        stmts.append(self.diff_description(inindex))
        return stmts


class IndexDict(DbObjectDict):
    "The collection of indexes on tables in a database"

    cls = Index
    query = \
        """SELECT nspname AS schema, indrelid::regclass AS table,
                  c.relname AS name, amname AS access_method,
                  indisunique AS unique, indkey AS keycols,
                  pg_get_expr(indexprs, indrelid) AS expression,
                  pg_get_indexdef(indexrelid) AS defn,
                  obj_description (c.oid, 'pg_class') AS description
           FROM pg_index JOIN pg_class c ON (indexrelid = c.oid)
                JOIN pg_namespace ON (relnamespace = pg_namespace.oid)
                JOIN pg_am ON (relam = pg_am.oid)
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
            if index.keycols != '0':
                index.columns = []
                for col in index.defn[index.defn.rfind('(') + 1:-1].split(','):
                    opts = col.lstrip().split()
                    nm = opts[0]
                    extra = {}
                    for i, opt in enumerate(opts[1:]):
                        if opt.upper() not in ['ASC', 'DESC', 'NULLS',
                                               'FIRST', 'LAST']:
                            extra.update(opclass=opt)
                            continue
                        elif opt == 'NULLS':
                            extra.update(nulls=opts[i + 2].lower())
                        elif opt == 'DESC':
                            extra.update(order='desc')
                        else:
                            continue
                    if extra:
                        index.columns.append({nm: extra})
                    else:
                        index.columns.append(nm)
            del index.defn, index.keycols
            self[(sch, tbl, idx)] = index

    def from_map(self, table, inindexes):
        """Initialize the dictionary of indexes by converting the input map

        :param table: table owning the indexes
        :param inindexes: YAML map defining the indexes
        """
        for i in inindexes.keys():
            idx = Index(schema=table.schema, table=table.name, name=i)
            val = inindexes[i]
            if 'columns' in val:
                idx.columns = val['columns']
            elif 'expression' in val:
                idx.expression = val['expression']
            else:
                raise KeyError("Index '%s' is missing columns or expression"
                               % i)
            for attr in ['access_method', 'unique']:
                if attr in val:
                    setattr(idx, attr, val[attr])
            if not hasattr(idx, 'unique'):
                idx.unique = False
            if 'description' in val:
                idx.description = val['description']
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
        for (sch, tbl, idx) in inindexes.keys():
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
        for (sch, tbl, idx) in self.keys():
            index = self[(sch, tbl, idx)]
            # if missing, drop it
            if (sch, tbl, idx) not in inindexes:
                stmts.append(index.drop())
            else:
                # compare index objects
                stmts.append(index.diff_map(inindexes[(sch, tbl, idx)]))

        return stmts
