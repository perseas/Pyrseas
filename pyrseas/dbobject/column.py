# -*- coding: utf-8 -*-
"""
    pyrseas.column
    ~~~~~~~~~~~~~~

    This module defines two classes: Column derived from
    DbSchemaObject and ColumnDict derived from DbObjectDict.
"""
from pyrseas.dbobject import DbObjectDict, DbSchemaObject
from pyrseas.dbobject import quote_id, grantable
from pyrseas.dbobject.privileges import privileges_from_map, add_grant
from pyrseas.dbobject.privileges import diff_privs


class Column(DbSchemaObject):
    "A table column definition"

    keylist = ['schema', 'table']
    allprivs = 'arwx'

    def to_map(self, no_privs):
        """Convert a column to a YAML-suitable format

        :param no_privs: exclude privilege information
        :return: dictionary
        """
        if hasattr(self, 'dropped'):
            return None
        dct = self._base_map(False, no_privs)
        del dct['number'], dct['name']
        if '_table' in dct:
            del dct['_table']
        if '_type' in dct:
            del dct['_type']
        if 'collation' in dct and dct['collation'] == 'default':
            del dct['collation']
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
        if hasattr(self, 'collation') and self.collation != 'default':
            stmt += ' COLLATE ' + self.collation
        return (stmt, '' if not hasattr(self, 'description')
                else self.comment())

    def add_privs(self):
        """Generate SQL statements to grant privileges on new column

        :return: list of SQL statements
        """
        stmts = []
        if hasattr(self, 'privileges'):
            for priv in self.privileges:
                stmts.append(add_grant(self._table, priv, self.name))
        return stmts

    def diff_privileges(self, incol):
        """Generate SQL statements to grant or revoke privileges

        :param incol: a YAML map defining the input column
        :return: list of SQL statements
        """
        stmts = []
        currprivs = self.privileges if hasattr(self, 'privileges') else {}
        newprivs = incol.privileges if hasattr(incol, 'privileges') else {}
        stmts.append(diff_privs(self._table, currprivs, incol._table, newprivs,
                                self.name))
        return stmts

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
            (comptype, objtype) = (self._table.objtype, 'COLUMN')
            compname = self._table.qualname()
        elif hasattr(self, '_type'):
            (comptype, objtype) = ('TYPE', 'ATTRIBUTE')
            compname = self._type.qualname()
        else:
            raise TypeError("Cannot determine type of %s", self.name)
        return "ALTER %s %s DROP %s %s" % (comptype, compname, objtype,
                                           self.name)

    def rename(self, newname):
        """Return SQL statement to RENAME the column

        :param newname: the new name of the object
        :return: SQL statement
        """
        if hasattr(self, '_table'):
            (comptype, objtype) = (self._table.objtype, 'COLUMN')
            compname = self._table.qualname()
        elif hasattr(self, '_type'):
            (comptype, objtype) = ('TYPE', 'ATTRIBUTE')
            compname = self._type.qualname()
        else:
            raise TypeError("Cannot determine type of %s", self.name)
        stmt = "ALTER %s %s RENAME %s %s TO %s" % (
            comptype, compname, objtype, self.name, newname)
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


QUERY_PRE91 = \
        """SELECT nspname AS schema, relname AS table, attname AS name,
                  attnum AS number, format_type(atttypid, atttypmod) AS type,
                  attnotnull AS not_null, attinhcount AS inherited,
                  pg_get_expr(adbin, adrelid) AS default,
                  attisdropped AS dropped,
                  array_to_string(attacl, ',') AS privileges,
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


class ColumnDict(DbObjectDict):
    "The collection of columns in tables in a database"

    cls = Column
    query = \
        """SELECT nspname AS schema, relname AS table, attname AS name,
                  attnum AS number, format_type(atttypid, atttypmod) AS type,
                  attnotnull AS not_null, attinhcount AS inherited,
                  pg_get_expr(adbin, adrelid) AS default,
                  collname AS collation, attisdropped AS dropped,
                  array_to_string(attacl, ',') AS privileges,
                  col_description(c.oid, attnum) AS description
           FROM pg_attribute JOIN pg_class c ON (attrelid = c.oid)
                JOIN pg_namespace ON (relnamespace = pg_namespace.oid)
                LEFT JOIN pg_attrdef ON (attrelid = pg_attrdef.adrelid
                     AND attnum = pg_attrdef.adnum)
                LEFT JOIN pg_collation l ON (attcollation = l.oid)
           WHERE relkind in ('c', 'r', 'f')
                 AND (nspname != 'pg_catalog'
                      AND nspname != 'information_schema')
                 AND attnum > 0
           ORDER BY nspname, relname, attnum"""

    def _from_catalog(self):
        """Initialize the dictionary of columns by querying the catalogs"""
        if self.dbconn.version < 90100:
            self.query = QUERY_PRE91
        for col in self.fetch():
            if hasattr(col, 'privileges'):
                col.privileges = col.privileges.split(',')
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

        for incol in incols:
            for key in list(incol.keys()):
                if isinstance(incol[key], dict):
                    arg = incol[key]
                else:
                    arg = {'type': incol[key]}
                col = Column(schema=table.schema, table=table.name, name=key,
                             **arg)
                if hasattr(col, 'privileges'):
                    if not hasattr(table, 'owner'):
                        raise ValueError("Column '%s.%s' has privileges but "
                                         "no owner information" % (
                                table.name, key))
                    col.privileges = privileges_from_map(
                                col.privileges, col.allprivs, table.owner)
                cols.append(col)

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

        for (sch, tbl) in list(incols.keys()):
            if (sch, tbl) in list(self.keys()):
                for col in self[(sch, tbl)]:
                    if col.name not in [c.name for c in incols[(sch, tbl)]] \
                            and not hasattr(col, 'dropped') \
                            and not hasattr(col, 'inherited'):
                        stmts.append(col.drop())

        return stmts
