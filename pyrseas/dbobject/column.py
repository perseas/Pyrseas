# -*- coding: utf-8 -*-
"""
    pyrseas.column
    ~~~~~~~~~~~~~~

    This module defines two classes: Column derived from
    DbSchemaObject and ColumnDict derived from DbObjectDict.
"""
from pyrseas.dbobject import DbObjectDict, DbSchemaObject, quote_id


class Column(DbSchemaObject):
    "A table column definition"

    keylist = ['schema', 'table']

    def to_map(self):
        """Convert a column to a YAML-suitable format

        :return: dictionary
        """
        if hasattr(self, 'dropped'):
            return None
        dct = self._base_map()
        del dct['number'], dct['name'], dct['_table']
        if hasattr(self, 'inherited'):
            dct['inherited'] = (self.inherited != 0)
        return {self.name: dct}

    def add(self):
        """Return a string to specify the column in a CREATE or ALTER TABLE

        :return: partial SQL statement
        """
        stmt = "%s %s" % (quote_id(self.name), self.type)
        if hasattr(self, 'not_null'):
            stmt += ' NOT NULL'
        if hasattr(self, 'default'):
            if not self.default.startswith('nextval'):
                stmt += ' DEFAULT ' + self.default
        return (stmt, '' if not hasattr(self, 'description')
                else self.comment())

    def comment(self):
        """Return a SQL COMMENT statement for the column

        :return: SQL statement
        """
        return "COMMENT ON COLUMN %s.%s IS %s" % (
            self._table.qualname(), self.name, self._comment_text())

    def drop(self):
        """Return string to drop the column via ALTER TABLE

        :return: SQL statement
        """
        if hasattr(self, 'dropped'):
            return ""
        if hasattr(self, '_table'):
            (contype, objtype) = (self._table.objtype, 'COLUMN')
        else:
            (contype, objtype) = ('TYPE', 'ATTRIBUTE')
        return "ALTER %s %s DROP %s %s" % (contype, self.table, objtype,
                                           self.name)

    def rename(self, newname):
        """Return SQL statement to RENAME the column

        :param newname: the new name of the object
        :return: SQL statement
        """
        stmt = "ALTER TABLE %s RENAME COLUMN %s TO %s" % (
            self._table.qualname(), self.name, newname)
        self.name = newname
        return stmt

    def set_sequence_default(self):
        """Return SQL statements to set a nextval() DEFAULT

        :return: list of SQL statements
        """
        stmts = []
        pth = self.set_search_path()
        if pth:
            stmts.append(pth)
        stmts.append("ALTER TABLE %s ALTER COLUMN %s SET DEFAULT %s" % (
                quote_id(self.table), quote_id(self.name), self.default))
        return stmts

    def diff_map(self, incol):
        """Generate SQL to transform an existing column

        :param insequence: a YAML map defining the new column
        :return: list of partial SQL statements

        Compares the column to an input column and generates partial
        SQL statements to transform it into the one represented by the
        input.
        """
        stmts = []
        base = "ALTER COLUMN %s " % self.name
        # check NOT NULL
        if not hasattr(self, 'not_null') and hasattr(incol, 'not_null'):
            stmts.append(base + "SET NOT NULL")
        if hasattr(self, 'not_null') and not hasattr(incol, 'not_null'):
            stmts.append(base + "DROP NOT NULL")
        # check data types
        if not hasattr(self, 'type'):
            raise ValueError("Column '%s' missing datatype" % self.name)
        if not hasattr(incol, 'type'):
            raise ValueError("Input column '%s' missing datatype" % incol.name)
        if self.type != incol.type:
            # validate type conversion?
            stmts.append(base + "TYPE %s" % incol.type)
        # check DEFAULTs
        if not hasattr(self, 'default') and hasattr(incol, 'default'):
            stmts.append(base + "SET DEFAULT %s" % incol.default)
        if hasattr(self, 'default') and not hasattr(incol, 'default'):
            stmts.append(base + "DROP DEFAULT")
        return (", ".join(stmts), self.diff_description(incol))


class ColumnDict(DbObjectDict):
    "The collection of columns in tables in a database"

    cls = Column
    query = \
        """SELECT nspname AS schema, relname AS table, attname AS name,
                  attnum AS number, format_type(atttypid, atttypmod) AS type,
                  attnotnull AS not_null, attinhcount AS inherited,
                  pg_get_expr(adbin, adrelid) AS default,
                  attisdropped AS dropped,
                  col_description(c.oid, attnum) AS description
           FROM pg_attribute JOIN pg_class c ON (attrelid = c.oid)
                JOIN pg_namespace ON (relnamespace = pg_namespace.oid)
                LEFT JOIN pg_attrdef ON (attrelid = pg_attrdef.adrelid
                     AND attnum = pg_attrdef.adnum)
           WHERE relkind in ('c', 'r', 'f')
                 AND (nspname != 'pg_catalog'
                      AND nspname != 'information_schema')
                 AND attnum > 0
           ORDER BY nspname, relname, attnum"""

    def _from_catalog(self):
        """Initialize the dictionary of columns by querying the catalogs"""
        for col in self.fetch():
            sch, tbl = col.key()
            if (sch, tbl) not in self:
                self[(sch, tbl)] = []
            self[(sch, tbl)].append(col)

    def from_map(self, table, incols):
        """Initialize the dictionary of columns by converting the input list

        :param table: table or type owning the columns/attributes
        :param incols: YAML list defining the columns
        """
        if not incols:
            raise ValueError("Table '%s' has no columns" % table.name)
        cols = self[(table.schema, table.name)] = []

        for col in incols:
            for key in col.keys():
                if isinstance(col[key], dict):
                    arg = col[key]
                else:
                    arg = {'type': col[key]}
                cols.append(Column(schema=table.schema, table=table.name,
                                   name=key, **arg))

    def diff_map(self, incols):
        """Generate SQL to transform existing columns

        :param incols: a YAML map defining the new columns
        :return: list of SQL statements

        Compares the existing column definitions, as fetched from the
        catalogs, to the input map and generates SQL statements to
        transform the columns accordingly.

        This takes care of dropping columns that are not present in
        the input map.  It's separate so that it can be done last,
        after other table, constraint and index changes.
        """
        stmts = []
        if not incols or not self:
            return stmts

        for (sch, tbl) in incols.keys():
            if (sch, tbl) in self.keys():
                for col in self[(sch, tbl)]:
                    if col.name not in [c.name for c in incols[(sch, tbl)]] \
                            and not hasattr(col, 'dropped'):
                        stmts.append(col.drop())

        return stmts
