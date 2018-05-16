# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.column
    ~~~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: Column derived from
    DbSchemaObject and ColumnDict derived from DbObjectDict.
"""
from . import DbObjectDict, DbSchemaObject, quote_id
from .privileges import privileges_from_map, add_grant, diff_privs


IDENTITY_TYPES = {'a': 'always', 'd': 'by default'}


class Column(DbSchemaObject):
    "A table column or attribute of a composite type"

    keylist = ['schema', 'table']    # plus attribute number
    allprivs = 'arwx'

    def __init__(self, name, schema, table, number, type, description=None,
                 privileges=[], not_null=True, default=None, identity=None,
                 collation=None, statistics=None, inherited=False,
                 dropped=False):
        """Initialize the column

        :param name: column/attribute name (from attname)
        :param schema: schema name (from nspname attrelid/relnamespace)
        :param table: table/composite type name (from relame via attrelid)
        :param description: comment text (from obj_description())
        :param privileges: access privileges (from attacl)
        :param number: attribute number (from attnum)
        :param type: data type (from atttypid/atttypmod)
        :param not_null: not null constraint (from attnotnull)
        :param default: default value expression (from pg_attrdef.adbin)
        :param identity: type of identity column (from attidentity)
        :param collation: collation name (from collname via attcollation)
        :param statistics: statistics detail level (from attstattarget)
        :param inherited: inherited indicator (from attinhcount)
        :param dropped: dropped indicator (from attisdropped)
        """
        super(Column, self).__init__(name, schema, description)
        self._init_own_privs(None, privileges)
        self.table = table
        self.number = number
        self.type = type
        self.not_null = not_null
        self.default = default
        if identity == '' or identity is None:
            self.identity = None
        elif identity is not None and len(identity) == 1:
            self.identity = IDENTITY_TYPES[identity]
        else:
            self.identity = identity
        assert self.identity is None or \
            self.identity in IDENTITY_TYPES.values()
        self.collation = collation
        self.statistics = statistics
        self.inherited = inherited
        self.dropped = dropped
        self._table = None
        self._type = None

    @staticmethod
    def query(dbversion=None):
        qry = """
            SELECT nspname AS schema, relname AS table, attname AS name,
                   attnum AS number, format_type(atttypid, atttypmod) AS type,
                   attnotnull AS not_null, attinhcount > 0 AS inherited,
                   pg_get_expr(adbin, adrelid) AS default, %s AS identity,
                   attstattarget AS statistics,
                   collname AS collation, attisdropped AS dropped,
                   array_to_string(attacl, ',') AS privileges,
                   col_description(c.oid, attnum) AS description
            FROM pg_attribute JOIN pg_class c ON (attrelid = c.oid)
                 JOIN pg_namespace ON (relnamespace = pg_namespace.oid)
                 LEFT JOIN pg_attrdef ON (attrelid = pg_attrdef.adrelid
                      AND attnum = pg_attrdef.adnum)
                 LEFT JOIN pg_collation l ON (attcollation = l.oid)
            WHERE relkind in ('c', 'r', 'f', 'p', 'v', 'm')
              AND (nspname != 'pg_catalog' AND nspname != 'information_schema')
              AND attnum > 0
           ORDER BY nspname, relname, attnum"""
        if dbversion < 100000:
            return qry % ("NULL")
        else:
            return qry % ("attidentity")

    @staticmethod
    def from_map(name, table, num, inobj):
        """Initialize a Column instance from a YAML map

        :param name: column name
        :param table: table map
        :param num: column number
        :param inobj: YAML map of the column
        :return: Column instance
        """
        obj = Column(
            name, table.schema, table.name, num, inobj.pop('type', None),
            inobj.pop('description', None), inobj.pop('privileges', []),
            inobj.pop('not_null', False), inobj.pop('default', None),
            inobj.pop('identity', None), inobj.pop('collation', None),
            inobj.pop('statistics', None), inobj.pop('inherited', False),
            inobj.pop('dropped', False))
        obj.set_oldname(inobj)
        if len(obj.privileges) > 0:
            if table.owner is None:
                raise ValueError("Column '%s.%s' has privileges but "
                                 "no owner information" % (table.name, name))
            obj.privileges = privileges_from_map(
                obj.privileges, obj.allprivs, table.owner)
        return obj

    def to_map(self, db, no_privs):
        """Convert a column to a YAML-suitable format

        :param no_privs: exclude privilege information
        :return: dictionary
        """
        if self.dropped:
            return None
        dct = super(Column, self).to_map(db, False, no_privs, deepcopy=False)
        del dct['number'], dct['name'], dct['dropped']
        if not self.not_null:
            dct.pop('not_null')
        if self.default is None:
            dct.pop('default')
        if self.identity is None:
            dct.pop('identity')
        if self.collation is None or self.collation == 'default':
            dct.pop('collation')
        if not self.inherited:
            dct.pop('inherited')
        if self.statistics is None or self.statistics == -1:
            dct.pop('statistics')
        return {self.name: dct}

    def add(self):
        """Return a string to specify the column in a CREATE or ALTER TABLE

        :return: partial SQL statement
        """
        stmt = "%s %s" % (quote_id(self.name), self.type)
        if self.not_null:
            stmt += ' NOT NULL'
        if self.default is not None:
            stmt += ' DEFAULT ' + self.default
        if self.identity is not None:
            stmt += " GENERATED %s AS IDENTITY" % self.identity.upper()
            stmt += " (%s)" % self._owner_seq.add_inline()
        if self.collation is not None and self.collation != 'default':
            stmt += ' COLLATE "%s"' % self.collation
        return (stmt, '' if self.description is None else self.comment())

    def add_privs(self):
        """Generate SQL statements to grant privileges on new column

        :return: list of SQL statements
        """
        return [add_grant(self._table, priv, self.name)
                for priv in self.privileges]

    def diff_privileges(self, incol):
        """Generate SQL statements to grant or revoke privileges

        :param incol: a YAML map defining the input column
        :return: list of SQL statements
        """
        return [diff_privs(self._table, self.privileges, incol._table,
                           incol.privileges, self.name)]

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
        if self.dropped:
            return []
        if self._table is not None:
            (comptype, objtype) = (self._table.objtype, 'COLUMN')
            compname = self._table.qualname()
        elif self._type is not None:
            (comptype, objtype) = ('TYPE', 'ATTRIBUTE')
            compname = self._type.qualname()
        else:
            raise TypeError("Cannot determine type of %s", self.name)
        return "ALTER %s %s DROP %s %s" % (comptype, compname, objtype,
                                           quote_id(self.name))

    def rename(self, newname):
        """Return SQL statement to RENAME the column

        :param newname: the new name of the object
        :return: SQL statement
        """
        if self._table is not None:
            (comptype, objtype) = (self._table.objtype, 'COLUMN')
            compname = self._table.qualname()
        elif self._type is not None:
            (comptype, objtype) = ('TYPE', 'ATTRIBUTE')
            compname = self._type.qualname()
        else:
            raise TypeError("Cannot determine type of %s", self.name)
        stmt = "ALTER %s %s RENAME %s %s TO %s" % (
            comptype, compname, objtype, self.name, newname)
        self.name = newname
        return stmt

    def alter(self, incol):
        """Generate SQL to transform an existing column

        :param insequence: a YAML map defining the new column
        :return: list of partial SQL statements

        Compares the column to an input column and generates partial
        SQL statements to transform it into the one represented by the
        input.
        """
        stmts = []
        base = "ALTER COLUMN %s " % quote_id(self.name)
        # check NOT NULL
        if not self.not_null and incol.not_null:
            stmts.append(base + "SET NOT NULL")
        if self.not_null and not incol.not_null:
            stmts.append(base + "DROP NOT NULL")
        # check data types
        if self.type is None:
            raise ValueError("Column '%s' missing datatype" % self.name)
        if incol.type is None:
            raise ValueError("Input column '%s' missing datatype" % incol.name)
        if self.type != incol.type:
            # validate type conversion?
            stmts.append(base + "TYPE %s" % incol.type)
        # check DEFAULTs
        if self.default is None and incol.default is not None:
            stmts.append(base + "SET DEFAULT %s" % incol.default)
        if self.default is not None:
            if incol.default is None:
                stmts.append(base + "DROP DEFAULT")
            elif self.default != incol.default:
                stmts.append(base + "SET DEFAULT %s" % incol.default)
        # check STATISTICS
        if self.statistics is not None:
            if self.statistics == -1 and (incol.statistics is not None
                                          and incol.statistics != -1):
                stmts.append(base + "SET STATISTICS %d" % incol.statistics)
            if self.statistics != -1 and (incol.statistics is None
                                          or incol.statistics == -1):
                stmts.append(base + "SET STATISTICS -1")

        return (", ".join(stmts), self.diff_description(incol))


class ColumnDict(DbObjectDict):
    "The collection of columns in tables in a database"

    cls = Column

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

        for (num, incol) in enumerate(incols):
            for key in incol:
                if isinstance(incol[key], dict):
                    inobj = incol[key]
                else:
                    inobj = {'type': incol[key]}
                cols.append(Column.from_map(key, table, num, inobj))
