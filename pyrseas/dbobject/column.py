# -*- coding: utf-8 -*-
"""
    pyrseas.column
    ~~~~~~~~~~~~~~

    This module defines two classes: Column derived from
    DbSchemaObject and ColumnDict derived from DbObjectDict.
"""
from pyrseas.dbobject import DbObjectDict, DbSchemaObject


class Column(DbSchemaObject):
    "A table column definition"

    keylist = ['schema', 'table']

    def to_map(self):
        """Convert a column to a YAML-suitable format

        :return: dictionary
        """
        dct = self.__dict__.copy()
        for k in self.keylist:
            del dct[k]
        del dct['number'], dct['name']
        return {self.name: dct}

    def add(self):
        """Return a string to specify the column in a CREATE or ALTER TABLE

        :return: partial SQL statement
        """
        stmt = "%s %s" % (self.name, self.type)
        if hasattr(self, 'not_null'):
            stmt += ' NOT NULL'
        if hasattr(self, 'default'):
            if not self.default.startswith('nextval'):
                stmt += ' DEFAULT ' + self.default
        return stmt

    def drop(self):
        """Return string to drop the column via ALTER TABLE

        :return: SQL statement
        """
        return "ALTER TABLE %s DROP COLUMN %s" % (self.table, self.name)

    def set_sequence_default(self):
        """Return SQL statements to set a nextval() DEFAULT

        :return: list of SQL statements
        """
        stmts = []
        pth = self.set_search_path()
        if pth:
            stmts.append(pth)
        stmts.append("ALTER TABLE %s ALTER COLUMN %s SET DEFAULT %s" % (
                self.table, self.name, self.default))
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
        return ", ".join(stmts)


class ColumnDict(DbObjectDict):
    "The collection of columns in tables in a database"

    cls = Column
    query = \
        """SELECT nspname AS schema, relname AS table, attname AS name,
                  attnum AS number, format_type(atttypid, atttypmod) AS type,
                  attnotnull AS not_null, adsrc AS default
           FROM pg_attribute JOIN pg_class ON (attrelid =  pg_class.oid)
                JOIN pg_namespace ON (relnamespace = pg_namespace.oid)
                JOIN pg_roles ON (nspowner = pg_roles.oid)
                LEFT JOIN pg_attrdef ON (attrelid = pg_attrdef.adrelid
                     AND attnum = pg_attrdef.adnum)
           WHERE relkind = 'r'
                 AND (nspname = 'public' OR rolname <> 'postgres')
                 AND attnum > 0
                 AND NOT attisdropped
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

        :param table: table owning the columns
        :param incols: YAML list defining the columns
        """
        if not incols:
            raise ValueError("Table '%s' has no columns" % table.name)
        cols = self[(table.schema, table.name)] = []

        for col in incols:
            for key in col.keys():
                cols.append(Column(schema=table.schema, table=table.name,
                                   name=key, **col[key]))

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
        incolnames = [n.name for n in incols.values()[0]]
        for col in self.values()[0]:
            if col.name not in incolnames:
                stmts.append(col.drop())

        return stmts
