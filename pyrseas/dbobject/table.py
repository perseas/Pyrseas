# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.table
    ~~~~~~~~~~~~~~~~~~~~~~

    This module defines six classes: DbClass derived from
    DbSchemaObject, Sequence, Table and View derived from DbClass,
    MaterializedView derived from View, and ClassDict derived from
    DbObjectDict.
"""
import os
import sys

from pyrseas.lib.pycompat import PY2
from pyrseas.dbobject import DbObjectDict, DbSchemaObject
from pyrseas.dbobject import quote_id, split_schema_obj
from pyrseas.dbobject import commentable, ownable, grantable
from pyrseas.dbobject.constraint import CheckConstraint, PrimaryKey
from pyrseas.dbobject.constraint import ForeignKey, UniqueConstraint
from pyrseas.dbobject.privileges import privileges_from_map, add_grant

MAX_BIGINT = 9223372036854775807


class DbClass(DbSchemaObject):
    """A table, sequence or view"""

    keylist = ['schema', 'name']


class Sequence(DbClass):
    "A sequence generator definition"

    objtype = "SEQUENCE"

    @property
    def allprivs(self):
        return 'rwU'

    def get_attrs(self, dbconn):
        """Get the attributes for the sequence

        :param dbconn: a DbConnection object
        """
        data = dbconn.fetchone(
            """SELECT start_value, increment_by, max_value, min_value,
                      cache_value
               FROM %s.%s""" % (quote_id(self.schema), quote_id(self.name)))
        for key, val in list(data.items()):
            setattr(self, key, val)

    def get_dependent_table(self, dbconn):
        """Get the table and column name that uses or owns the sequence

        :param dbconn: a DbConnection object
        """
        data = dbconn.fetchone(
            """SELECT refobjid::regclass, refobjsubid
               FROM pg_depend
               WHERE objid = '%s'::regclass
                 AND refclassid = 'pg_class'::regclass""" % self.qualname())
        if data:
            (sch, self.owner_table) = split_schema_obj(data[0], self.schema)
            self.owner_column = data[1]
            return
        data = dbconn.fetchone(
            """SELECT adrelid::regclass
               FROM pg_attrdef a JOIN pg_depend ON (a.oid = objid)
               WHERE refobjid = '%s'::regclass
               AND classid = 'pg_attrdef'::regclass""" % self.qualname())
        if data:
            (sch, self.dependent_table) = split_schema_obj(
                data[0], self.schema)

    def to_map(self, opts):
        """Convert a sequence definition to a YAML-suitable format

        :param opts: options to include/exclude tables, etc.
        :return: dictionary
        """
        if hasattr(opts, 'tables') and opts.tables and \
                (self.name not in opts.tables and
                 not hasattr(self, 'owner_table') or
                 self.owner_table not in opts.tables) or (
                     hasattr(opts, 'excl_tables') and opts.excl_tables
                     and self.name in opts.excl_tables):
            return None
        seq = {}
        for key, val in list(self.__dict__.items()):
            if key in self.keylist or key == 'dependent_table' or (
                    key == 'owner' and opts.no_owner) or (
                    key == 'privileges' and opts.no_privs):
                continue
            if key == 'privileges':
                seq[key] = self.map_privs()
            elif key == 'max_value' and val == MAX_BIGINT:
                seq[key] = None
            elif key == 'min_value' and val == 1:
                seq[key] = None
            else:
                if PY2:
                    if isinstance(val, (int, long)) and val <= sys.maxsize:
                        seq[key] = int(val)
                    else:
                        seq[key] = str(val)
                else:
                    if isinstance(val, int):
                        seq[key] = int(val)
                    else:
                        seq[key] = str(val)

        return seq

    @commentable
    @grantable
    @ownable
    def create(self):
        """Return a SQL statement to CREATE the sequence

        :return: SQL statements
        """
        maxval = self.max_value and ("MAXVALUE %d" % self.max_value) \
            or "NO MAXVALUE"
        minval = self.min_value and ("MINVALUE %d" % self.min_value) \
            or "NO MINVALUE"
        return ["""CREATE SEQUENCE %s
    START WITH %d
    INCREMENT BY %d
    %s
    %s
    CACHE %d""" % (self.qualname(), self.start_value, self.increment_by,
                   maxval, minval, self.cache_value)]

    def add_owner(self):
        """Return statement to ALTER the sequence to indicate its owner table

        :return: SQL statement
        """
        stmts = []
        stmts.append("ALTER SEQUENCE %s OWNED BY %s.%s" % (
            self.qualname(), self.qualname(self.owner_table),
            quote_id(self.owner_column)))
        return stmts

    def diff_map(self, inseq):
        """Generate SQL to transform an existing sequence

        :param inseq: a YAML map defining the new sequence
        :return: list of SQL statements

        Compares the sequence to an input sequence and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []
        stmt = ""
        if self.start_value != inseq.start_value:
            stmt += " START WITH %d" % inseq.start_value
        if self.increment_by != inseq.increment_by:
            stmt += " INCREMENT BY %d" % inseq.increment_by
        maxval = self.max_value
        if maxval == MAX_BIGINT:
            maxval = None
        if maxval != inseq.max_value:
            stmt += inseq.max_value and (" MAXVALUE %d" % inseq.max_value) \
                or " NO MAXVALUE"
        minval = self.min_value
        if minval == 1:
            minval = None
        if minval != inseq.min_value:
            stmt += inseq.min_value and (" MINVALUE %d" % inseq.min_value) \
                or " NO MINVALUE"
        if self.cache_value != inseq.cache_value:
            stmt += " CACHE %d" % inseq.cache_value
        if stmt:
            stmts.append("ALTER SEQUENCE %s" % self.qualname() + stmt)

        if hasattr(inseq, 'owner'):
            if inseq.owner != self.owner:
                stmts.append(self.alter_owner(inseq.owner))
        stmts.append(self.diff_privileges(inseq))
        stmts.append(self.diff_description(inseq))
        return stmts


class Table(DbClass):
    """A database table definition

    A table is identified by its schema name and table name.  It should
    have a list of columns.  It may have a primary_key, zero or more
    foreign_keys, zero or more unique_constraints, and zero or more
    indexes.
    """

    objtype = "TABLE"

    @property
    def allprivs(self):
        return 'arwdDxt'

    def column_names(self):
        """Return a list of column names in the table

        :return: list
        """
        return [c.name for c in self.columns]

    def to_map(self, dbschemas, opts):
        """Convert a table to a YAML-suitable format

        :param dbschemas: database dictionary of schemas
        :param opts: options to include/exclude tables, etc.
        :return: dictionary
        """
        if hasattr(opts, 'excl_tables') and opts.excl_tables \
                and self.name in opts.excl_tables or \
                not hasattr(self, 'columns'):
            return None
        cols = []
        for column in self.columns:
            col = column.to_map(opts.no_privs)
            if col:
                cols.append(col)
        tbl = {'columns': cols}
        attrlist = ['description', 'options', 'tablespace', 'unlogged']
        if not opts.no_owner:
            attrlist.append('owner')
        for attr in attrlist:
            if hasattr(self, attr):
                tbl.update({attr: getattr(self, attr)})
        if hasattr(self, 'check_constraints'):
            if not 'check_constraints' in tbl:
                tbl.update(check_constraints={})
            for k in list(self.check_constraints.values()):
                tbl['check_constraints'].update(
                    self.check_constraints[k.name].to_map(self.column_names()))
        if hasattr(self, 'primary_key'):
            tbl.update(primary_key=self.primary_key.to_map(
                self.column_names()))
        if hasattr(self, 'foreign_keys'):
            if not 'foreign_keys' in tbl:
                tbl['foreign_keys'] = {}
            for k in list(self.foreign_keys.values()):
                tbls = dbschemas[k.ref_schema].tables
                tbl['foreign_keys'].update(self.foreign_keys[k.name].to_map(
                    self.column_names(),
                    tbls[self.foreign_keys[k.name].ref_table]. column_names()))
        if hasattr(self, 'unique_constraints'):
            if not 'unique_constraints' in tbl:
                tbl.update(unique_constraints={})
            for k in list(self.unique_constraints.values()):
                tbl['unique_constraints'].update(
                    self.unique_constraints[k.name].to_map(
                        self.column_names()))
        if hasattr(self, 'indexes'):
            if not 'indexes' in tbl:
                tbl['indexes'] = {}
            for k in list(self.indexes.values()):
                tbl['indexes'].update(self.indexes[k.name].to_map())
        if hasattr(self, 'inherits'):
            if not 'inherits' in tbl:
                tbl['inherits'] = self.inherits
        if hasattr(self, 'rules'):
            if not 'rules' in tbl:
                tbl['rules'] = {}
            for k in list(self.rules.values()):
                tbl['rules'].update(self.rules[k.name].to_map())
        if hasattr(self, 'triggers'):
            if not 'triggers' in tbl:
                tbl['triggers'] = {}
            for k in list(self.triggers.values()):
                tbl['triggers'].update(self.triggers[k.name].to_map())

        if not opts.no_privs and hasattr(self, 'privileges'):
            tbl.update({'privileges': self.map_privs()})

        return tbl

    def create(self):
        """Return SQL statements to CREATE the table

        :return: SQL statements
        """
        stmts = []
        if hasattr(self, 'created'):
            return stmts
        cols = []
        colprivs = []
        for col in self.columns:
            if not (hasattr(col, 'inherited') and col.inherited):
                cols.append("    " + col.add()[0])
            colprivs.append(col.add_privs())
        unlogged = ''
        if hasattr(self, 'unlogged') and self.unlogged:
            unlogged = 'UNLOGGED '
        inhclause = ''
        if hasattr(self, 'inherits'):
            inhclause = " INHERITS (%s)" % ", ".join(t for t in self.inherits)
        opts = ''
        if hasattr(self, 'options'):
            opts = " WITH (%s)" % ', '.join(self.options)
        tblspc = ''
        if hasattr(self, 'tablespace'):
            tblspc = " TABLESPACE %s" % self.tablespace
        stmts.append("CREATE %sTABLE %s (\n%s)%s%s%s" % (
            unlogged, self.qualname(), ",\n".join(cols), inhclause, opts,
            tblspc))
        if hasattr(self, 'owner'):
            stmts.append(self.alter_owner())
        if hasattr(self, 'privileges'):
            for priv in self.privileges:
                stmts.append(add_grant(self, priv))
        if colprivs:
            stmts.append(colprivs)
        if hasattr(self, 'description'):
            stmts.append(self.comment())
        for col in self.columns:
            if hasattr(col, 'description'):
                stmts.append(col.comment())
        self.created = True
        return stmts

    def drop(self):
        """Return a SQL DROP statement for the table

        :return: SQL statement
        """
        stmts = []
        if not hasattr(self, 'dropped') or not self.dropped:
            if hasattr(self, 'dependent_funcs'):
                for fnc in self.dependent_funcs:
                    stmts.append(fnc.drop())
            self.dropped = True
            stmts.append("DROP TABLE %s" % self.identifier())
        return stmts

    def diff_options(self, newopts):
        """Compare options lists and generate SQL SET or RESET clause

        :newopts: list of new options
        :return: SQL SET / RESET clauses

        Generate ([SET|RESET storage_parameter=value) clauses from two
        lists in the form of 'key=value' strings.
        """
        def to_dict(optlist):
            return dict(opt.split('=', 1) for opt in optlist)

        oldopts = {}
        if hasattr(self, 'options'):
            oldopts = to_dict(self.options)
        newopts = to_dict(newopts)
        setclauses = []
        for key, val in list(newopts.items()):
            if key not in oldopts:
                setclauses.append("%s=%s" % (key, val))
            elif val != oldopts[key]:
                setclauses.append("%s=%s" % (key, val))
        resetclauses = []
        for key, val in list(oldopts.items()):
            if key not in newopts:
                resetclauses.append("%s" % key)
        clauses = ''
        if setclauses:
            clauses = "SET (%s)" % ', '.join(setclauses)
            if resetclauses:
                clauses += ', '
        if resetclauses:
            clauses += "RESET (%s)" % ', '.join(resetclauses)
        return clauses

    def diff_map(self, intable):
        """Generate SQL to transform an existing table

        :param intable: a YAML map defining the new table
        :return: list of SQL statements

        Compares the table to an input table and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []
        if not hasattr(intable, 'columns'):
            raise KeyError("Table '%s' has no columns" % intable.name)
        colnames = [col.name for col in self.columns
                    if not hasattr(col, 'dropped')]
        dbcols = len(colnames)

        colprivs = []
        base = "ALTER %s %s\n    " % (self.objtype, self.qualname())
        # check input columns
        for (num, incol) in enumerate(intable.columns):
            if hasattr(incol, 'oldname'):
                assert(self.columns[num].name == incol.oldname)
                stmts.append(self.columns[num].rename(incol.name))
            # check existing columns
            if num < dbcols and self.columns[num].name == incol.name:
                (stmt, descr) = self.columns[num].diff_map(incol)
                if stmt:
                    stmts.append(base + stmt)
                colprivs.append(self.columns[num].diff_privileges(incol))
                if descr:
                    stmts.append(descr)
            # add new columns
            elif incol.name not in colnames and \
                    not hasattr(incol, 'inherited'):
                (stmt, descr) = incol.add()
                stmts.append(base + "ADD COLUMN %s" % stmt)
                colprivs.append(incol.add_privs())
                if descr:
                    stmts.append(descr)

        newopts = []
        if hasattr(intable, 'options'):
            newopts = intable.options
        diff_opts = self.diff_options(newopts)
        if diff_opts:
            stmts.append("ALTER %s %s %s" % (self.objtype, self.identifier(),
                                             diff_opts))
        if hasattr(intable, 'owner'):
            if intable.owner != self.owner:
                stmts.append(self.alter_owner(intable.owner))
        stmts.append(self.diff_privileges(intable))
        if colprivs:
            stmts.append(colprivs)
        if hasattr(intable, 'tablespace'):
            if not hasattr(self, 'tablespace') \
                    or self.tablespace != intable.tablespace:
                stmts.append(base + "SET TABLESPACE %s"
                             % quote_id(intable.tablespace))
        elif hasattr(self, 'tablespace'):
            stmts.append(base + "SET TABLESPACE pg_default")

        stmts.append(self.diff_description(intable))

        return stmts

    def data_export(self, dbconn, dirpath):
        """Copy table data out to a file

        :param dbconn: database connection to use
        :param dirpath: full path to the directory for the file to be created
        """
        filepath = os.path.join(dirpath, self.extern_filename('data'))
        dbconn.copy_to(filepath, self.qualname())

    def data_import(self, dirpath):
        """Generate SQL to import data into a table

        :param dirpath: full path for the directory for the file
        :return: list of SQL statements
        """
        filepath = os.path.join(dirpath, self.extern_filename('data'))
        stmts = []
        if hasattr(self, 'referred_by'):
            stmts.append("ALTER TABLE %s DROP CONSTRAINT %s" % (
                self.referred_by._table.qualname(), self.referred_by.name))
        stmts.append("TRUNCATE ONLY %s" % self.qualname())
        stmts.append(("\\copy ", self.qualname(), " from '", filepath,
                      "' csv"))
        if hasattr(self, 'referred_by'):
            stmts.append(self.referred_by.add())
        return stmts


class View(DbClass):
    """A database view definition

    A view is identified by its schema name and view name.
    """

    objtype = "VIEW"
    privobjtype = "TABLE"

    @property
    def allprivs(self):
        return 'arwdDxt'

    def to_map(self, opts):
        """Convert a view to a YAML-suitable format

        :param opts: options to include/exclude tables, etc.
        :return: dictionary
        """
        if hasattr(opts, 'excl_tables') and opts.excl_tables \
                and self.name in opts.excl_tables:
            return None
        view = self._base_map(opts.no_owner, opts.no_privs)
        if 'dependent_funcs' in view:
            del view['dependent_funcs']
        if hasattr(self, 'triggers'):
            for key in list(self.triggers.values()):
                view['triggers'].update(self.triggers[key.name].to_map())
        return view

    @commentable
    @grantable
    @ownable
    def create(self, newdefn=None):
        """Return SQL statements to CREATE the table

        :return: SQL statements
        """
        defn = newdefn or self.definition
        if defn[-1:] == ';':
            defn = defn[:-1]
        return ["CREATE%s VIEW %s AS\n   %s" % (
                newdefn and " OR REPLACE" or '', self.qualname(), defn)]

    def diff_map(self, inview):
        """Generate SQL to transform an existing view

        :param inview: a YAML map defining the new view
        :return: list of SQL statements

        Compares the view to an input view and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []
        if self.definition != inview.definition:
            stmts.append(self.create(inview.definition))
        if hasattr(inview, 'owner'):
            if inview.owner != self.owner:
                stmts.append(self.alter_owner(inview.owner))
        stmts.append(self.diff_privileges(inview))
        stmts.append(self.diff_description(inview))
        return stmts


class MaterializedView(View):
    """A materialized view definition

    A materialized view is identified by its schema name and view name.
    """

    objtype = "MATERIALIZED VIEW"

    def to_map(self, opts):
        """Convert a materialized view to a YAML-suitable format

        :param opts: options to include/exclude tables, etc.
        :return: dictionary
        """
        if hasattr(opts, 'excl_tables') and opts.excl_tables \
                and self.name in opts.excl_tables:
            return None
        mvw = self._base_map(opts.no_owner, opts.no_privs)
        if hasattr(self, 'indexes'):
            if not 'indexes' in mvw:
                mvw['indexes'] = {}
            for k in list(self.indexes.values()):
                mvw['indexes'].update(self.indexes[k.name].to_map())
        return mvw

    @commentable
    @grantable
    @ownable
    def create(self, newdefn=None):
        """Return SQL statements to CREATE the materialized view

        :return: SQL statements
        """
        defn = newdefn or self.definition
        if defn[-1:] == ';':
            defn = defn[:-1]
        return ["CREATE %s %s AS\n   %s" % (
                self.objtype, self.qualname(), defn)]

    def diff_map(self, inview):
        """Generate SQL to transform an existing materialized view

        :param inview: a YAML map defining the new view
        :return: list of SQL statements

        Compares the view to an input view and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []
        if self.definition != inview.definition:
            stmts.append(self.create(inview.definition))
        if hasattr(inview, 'owner'):
            if inview.owner != self.owner:
                stmts.append(self.alter_owner(inview.owner))
        stmts.append(self.diff_privileges(inview))
        stmts.append(self.diff_description(inview))
        return stmts


QUERY_PRE91 = \
    """SELECT nspname AS schema, relname AS name, relkind AS kind,
              reloptions AS options, spcname AS tablespace,
              rolname AS owner, array_to_string(relacl, ',') AS privileges,
              CASE WHEN relkind = 'v' THEN pg_get_viewdef(c.oid, TRUE)
                   ELSE '' END AS definition,
              obj_description(c.oid, 'pg_class') AS description
       FROM pg_class c
            JOIN pg_roles r ON (r.oid = relowner)
            JOIN pg_namespace ON (relnamespace = pg_namespace.oid)
            LEFT JOIN pg_tablespace t ON (reltablespace = t.oid)
       WHERE relkind in ('r', 'S', 'v')
             AND (nspname != 'pg_catalog'
                  AND nspname != 'information_schema')
       ORDER BY nspname, relname"""

QUERY_PRE93 = \
    """SELECT nspname AS schema, relname AS name, relkind AS kind,
              reloptions AS options, relpersistence AS persistence,
              spcname AS tablespace, rolname AS owner,
              array_to_string(relacl, ',') AS privileges,
              CASE WHEN relkind = 'v' THEN pg_get_viewdef(c.oid, TRUE)
                   ELSE '' END AS definition,
              obj_description(c.oid, 'pg_class') AS description
       FROM pg_class c
            JOIN pg_roles r ON (r.oid = relowner)
            JOIN pg_namespace ON (relnamespace = pg_namespace.oid)
            LEFT JOIN pg_tablespace t ON (reltablespace = t.oid)
       WHERE relkind in ('r', 'S', 'v')
             AND (nspname != 'pg_catalog'
                  AND nspname != 'information_schema')
       ORDER BY nspname, relname"""

OBJTYPES = ['table', 'sequence', 'view', 'materialized view']


class ClassDict(DbObjectDict):
    "The collection of tables and similar objects in a database"

    cls = DbClass
    query = \
        """SELECT nspname AS schema, relname AS name, relkind AS kind,
                  reloptions AS options, relpersistence AS persistence,
                  spcname AS tablespace, rolname AS owner,
                  array_to_string(relacl, ',') AS privileges,
                  CASE WHEN relkind ~ '[vm]' THEN pg_get_viewdef(c.oid, TRUE)
                       ELSE '' END AS definition,
                  CASE WHEN relkind = 'm' THEN relispopulated
                       ELSE FALSE END AS with_data,
                  obj_description(c.oid, 'pg_class') AS description
           FROM pg_class c
                JOIN pg_roles r ON (r.oid = relowner)
                JOIN pg_namespace ON (relnamespace = pg_namespace.oid)
                LEFT JOIN pg_tablespace t ON (reltablespace = t.oid)
           WHERE relkind in ('r', 'S', 'v', 'm')
                 AND (nspname != 'pg_catalog'
                      AND nspname != 'information_schema')
           ORDER BY nspname, relname"""

    inhquery = \
        """SELECT inhrelid::regclass AS sub, inhparent::regclass AS parent,
                  inhseqno
           FROM pg_inherits
           ORDER BY 1, 3"""

    def _from_catalog(self):
        """Initialize the dictionary of tables by querying the catalogs"""
        if self.dbconn.version < 90100:
            self.query = QUERY_PRE91
        elif self.dbconn.version < 90300:
            self.query = QUERY_PRE93
        for table in self.fetch():
            sch, tbl = table.key()
            if hasattr(table, 'privileges'):
                table.privileges = table.privileges.split(',')
            if hasattr(table, 'persistence'):
                if table.persistence == 'u':
                    table.unlogged = True
                del table.persistence
            kind = table.kind
            del table.kind
            if kind == 'r':
                self[(sch, tbl)] = Table(**table.__dict__)
            elif kind == 'S':
                self[(sch, tbl)] = inst = Sequence(**table.__dict__)
                inst.get_attrs(self.dbconn)
                inst.get_dependent_table(self.dbconn)
            elif kind == 'v':
                self[(sch, tbl)] = View(**table.__dict__)
            elif kind == 'm':
                self[(sch, tbl)] = MaterializedView(**table.__dict__)
        inhtbls = self.dbconn.fetchall(self.inhquery)
        self.dbconn.rollback()
        for (tbl, partbl, num) in inhtbls:
            (sch, tbl) = split_schema_obj(tbl)
            table = self[(sch, tbl)]
            if not hasattr(table, 'inherits'):
                table.inherits = []
            table.inherits.append(partbl)

    def from_map(self, schema, inobjs, newdb):
        """Initalize the dictionary of tables by converting the input map

        :param schema: schema owning the tables
        :param inobjs: YAML map defining the schema objects
        :param newdb: collection of dictionaries defining the database
        """
        for k in inobjs:
            inobj = inobjs[k]
            objtype = None
            for typ in OBJTYPES:
                if k.startswith(typ):
                    objtype = typ
                    key = k[len(typ) + 1:]
            if objtype is None:
                raise KeyError("Unrecognized object type: %s" % k)
            if objtype == 'table':
                self[(schema.name, key)] = table = Table(
                    schema=schema.name, name=key)
                intable = inobj
                if not intable:
                    raise ValueError("Table '%s' has no specification" % k)
                for attr in ['inherits', 'owner', 'tablespace', 'oldname',
                             'description', 'options', 'unlogged']:
                    if attr in intable:
                        setattr(table, attr, intable[attr])
                try:
                    newdb.columns.from_map(table, intable['columns'])
                except KeyError as exc:
                    exc.args = ("Table '%s' has no columns" % key, )
                    raise
                newdb.constraints.from_map(table, intable)
                if 'indexes' in intable:
                    newdb.indexes.from_map(table, intable['indexes'])
                if 'rules' in intable:
                    newdb.rules.from_map(table, intable['rules'])
                if 'triggers' in intable:
                    newdb.triggers.from_map(table, intable['triggers'])
            elif objtype == 'sequence':
                self[(schema.name, key)] = seq = Sequence(
                    schema=schema.name, name=key)
                inseq = inobj
                if not inseq:
                    raise ValueError("Sequence '%s' has no specification" % k)
                for attr, val in list(inseq.items()):
                    setattr(seq, attr, val)
            elif objtype == 'view':
                self[(schema.name, key)] = view = View(
                    schema=schema.name, name=key)
                inview = inobj
                if not inview:
                    raise ValueError("View '%s' has no specification" % k)
                for attr, val in list(inview.items()):
                    setattr(view, attr, val)
                if 'triggers' in inview:
                    newdb.triggers.from_map(view, inview['triggers'])
            elif objtype == 'materialized view':
                self[(schema.name, key)] = mview = MaterializedView(
                    schema=schema.name, name=key)
                inmview = inobj
                if not inmview:
                    raise ValueError("View '%s' has no specification" % k)
                for attr, val in list(inmview.items()):
                    setattr(mview, attr, val)
            else:
                raise KeyError("Unrecognized object type: %s" % k)
            obj = self[(schema.name, key)]
            if 'privileges' in inobj:
                    if not hasattr(obj, 'owner'):
                        raise ValueError("%s '%s' has privileges but no "
                                         "owner information" %
                                         obj.objtype.capital(), table.name)
                    obj.privileges = privileges_from_map(
                        inobj['privileges'], obj.allprivs, obj.owner)

    def link_refs(self, dbcolumns, dbconstrs, dbindexes, dbrules, dbtriggers):
        """Connect columns, constraints, etc. to their respective tables

        :param dbcolumns: dictionary of columns
        :param dbconstrs: dictionary of constraints
        :param dbindexes: dictionary of indexes
        :param dbrules: dictionary of rules
        :param dbtriggers: dictionary of triggers

        Links each list of table columns in `dbcolumns` to the
        corresponding table. Fills the `foreign_keys`,
        `unique_constraints`, `indexes` and `triggers` dictionaries
        for each table by traversing the `dbconstrs`, `dbindexes` and
        `dbtriggers` dictionaries, which are keyed by schema, table
        and constraint, index or trigger name.
        """
        for (sch, tbl) in dbcolumns:
            if (sch, tbl) in self:
                assert isinstance(self[(sch, tbl)], Table)
                self[(sch, tbl)].columns = dbcolumns[(sch, tbl)]
                for col in dbcolumns[(sch, tbl)]:
                    col._table = self[(sch, tbl)]
        for (sch, tbl) in self:
            table = self[(sch, tbl)]
            if isinstance(table, Sequence) and hasattr(table, 'owner_table'):
                if isinstance(table.owner_column, int):
                    table.owner_column = self[(sch, table.owner_table)]. \
                        column_names()[table.owner_column - 1]
            elif isinstance(table, Table) and hasattr(table, 'inherits'):
                for partbl in table.inherits:
                    (parsch, partbl) = split_schema_obj(partbl)
                    assert self[(parsch, partbl)]
                    parent = self[(parsch, partbl)]
                    if not hasattr(parent, 'descendants'):
                        parent.descendants = []
                    parent.descendants.append(table)
        for (sch, tbl, cns) in dbconstrs:
            constr = dbconstrs[(sch, tbl, cns)]
            if hasattr(constr, 'target'):
                continue
            assert self[(sch, tbl)]
            constr._table = table = self[(sch, tbl)]
            if isinstance(constr, CheckConstraint):
                if not hasattr(table, 'check_constraints'):
                    table.check_constraints = {}
                table.check_constraints.update({cns: constr})
            elif isinstance(constr, PrimaryKey):
                table.primary_key = constr
            elif isinstance(constr, ForeignKey):
                if not hasattr(table, 'foreign_keys'):
                    table.foreign_keys = {}
                # link referenced and referrer
                constr.references = self[(constr.ref_schema, constr.ref_table)]
                # TODO: there can be more than one
                self[(constr.ref_schema, constr.ref_table)].referred_by = \
                    constr
                table.foreign_keys.update({cns: constr})
            elif isinstance(constr, UniqueConstraint):
                if not hasattr(table, 'unique_constraints'):
                    table.unique_constraints = {}
                table.unique_constraints.update({cns: constr})

        def link_one(targdict, schema, tbl, objkey, objtype):
            table = self[(schema, tbl)]
            if not hasattr(table, objtype):
                setattr(table, objtype, {})
            objdict = getattr(table, objtype)
            objdict.update({objkey: targdict[(schema, tbl, objkey)]})

        for (sch, tbl, idx) in dbindexes:
            link_one(dbindexes, sch, tbl, idx, 'indexes')
        for (sch, tbl, rul) in dbrules:
            link_one(dbrules, sch, tbl, rul, 'rules')
            dbrules[(sch, tbl, rul)]._table = self[(sch, tbl)]
        for (sch, tbl, trg) in dbtriggers:
            link_one(dbtriggers, sch, tbl, trg, 'triggers')
            dbtriggers[(sch, tbl, trg)]._table = self[(sch, tbl)]

    def _rename(self, obj, objtype):
        """Process a RENAME"""
        stmt = ''
        oldname = obj.oldname
        try:
            stmt = self[(obj.schema, oldname)].rename(obj.name)
            self[(obj.schema, obj.name)] = self[(obj.schema, oldname)]
            del self[(obj.schema, oldname)]
        except KeyError as exc:
            exc.args = ("Previous name '%s' for %s '%s' not found" % (
                oldname, objtype, obj.name), )
            raise
        return stmt

    def diff_map(self, intables):
        """Generate SQL to transform existing tables and sequences

        :param intables: a YAML map defining the new tables/sequences
        :return: list of SQL statements

        Compares the existing table/sequence definitions, as fetched
        from the catalogs, to the input map and generates SQL
        statements to transform the tables/sequences accordingly.
        """
        stmts = []
        # first pass: sequences owned by a table
        for (sch, seq) in intables:
            inseq = intables[(sch, seq)]
            if not isinstance(inseq, Sequence) or \
                    not hasattr(inseq, 'owner_table'):
                continue
            if (sch, seq) not in self:
                if hasattr(inseq, 'oldname'):
                    stmts.append(self._rename(inseq, "sequence"))
                else:
                    # create new sequence
                    stmts.append(inseq.create())

        # check input tables
        inhstack = []
        for (sch, tbl) in intables:
            intable = intables[(sch, tbl)]
            if not isinstance(intable, Table):
                continue
            # does it exist in the database?
            if (sch, tbl) not in self:
                if not hasattr(intable, 'oldname'):
                    # create new table
                    if hasattr(intable, 'inherits'):
                        inhstack.append(intable)
                    else:
                        stmts.append(intable.create())
                else:
                    stmts.append(self._rename(intable, "table"))
        while len(inhstack):
            intable = inhstack.pop()
            createit = True
            for partbl in intable.inherits:
                if intables[split_schema_obj(partbl)] in inhstack:
                    createit = False
            if createit:
                stmts.append(intable.create())
            else:
                inhstack.insert(0, intable)

        # check input views
        for (sch, tbl) in intables:
            intable = intables[(sch, tbl)]
            if not isinstance(intable, View):
                continue
            # does it exist in the database?
            if (sch, tbl) not in self:
                if hasattr(intable, 'oldname'):
                    stmts.append(self._rename(intable, "view"))
                else:
                    # create new view
                    stmts.append(intable.create())

        # second pass: input sequences not owned by tables
        for (sch, seq) in intables:
            inseq = intables[(sch, seq)]
            if not isinstance(inseq, Sequence):
                continue
            # does it exist in the database?
            if (sch, seq) not in self:
                if hasattr(inseq, 'oldname'):
                    stmts.append(self._rename(inseq, "sequence"))
                elif hasattr(inseq, 'owner_table'):
                    stmts.append(inseq.add_owner())
                else:
                    # create new sequence
                    stmts.append(inseq.create())

        # check database tables, sequences and views
        for (sch, tbl) in self:
            table = self[(sch, tbl)]
            # if missing, mark it for dropping
            if (sch, tbl) not in intables:
                table.dropped = False
            else:
                # check table/sequence/view objects
                stmts.append(table.diff_map(intables[(sch, tbl)]))

        # now drop the marked tables
        for (sch, tbl) in self:
            table = self[(sch, tbl)]
            if isinstance(table, Sequence) and hasattr(table, 'owner_table'):
                continue
            if hasattr(table, 'dropped') and not table.dropped:
                # first, drop all foreign keys
                if hasattr(table, 'foreign_keys'):
                    for fgn in table.foreign_keys:
                        stmts.append(table.foreign_keys[fgn].drop())
                # and drop the triggers
                if hasattr(table, 'triggers'):
                    for trg in table.triggers:
                        stmts.append(table.triggers[trg].drop())
                if hasattr(table, 'rules'):
                    for rul in table.rules:
                        stmts.append(table.rules[rul].drop())
                # drop views
                if isinstance(table, View):
                    stmts.append(table.drop())

        inhstack = []
        for (sch, tbl) in self:
            table = self[(sch, tbl)]
            if (isinstance(table, Sequence)
                    and (hasattr(table, 'owner_table')
                         or hasattr(table, 'dependent_table'))) \
                    or isinstance(table, View):
                continue
            if hasattr(table, 'dropped') and not table.dropped:
                # next, drop other subordinate objects
                if hasattr(table, 'check_constraints'):
                    for chk in table.check_constraints:
                        stmts.append(table.check_constraints[chk].drop())
                if hasattr(table, 'unique_constraints'):
                    for unq in table.unique_constraints:
                        stmts.append(table.unique_constraints[unq].drop())
                if hasattr(table, 'indexes'):
                    for idx in table.indexes:
                        stmts.append(table.indexes[idx].drop())
                if hasattr(table, 'rules'):
                    for rul in table.rules:
                        stmts.append(table.rules[rul].drop())
                if hasattr(table, 'primary_key'):
                    # TODO there can be more than one referred_by
                    if hasattr(table, 'referred_by'):
                        stmts.append(table.referred_by.drop())
                    stmts.append(table.primary_key.drop())
                # finally, drop the table itself
                if hasattr(table, 'descendants'):
                    inhstack.append(table)
                else:
                    stmts.append(table.drop())
        while len(inhstack):
            table = inhstack.pop()
            dropit = True
            for childtbl in table.descendants:
                if self[(childtbl.schema, childtbl.name)] in inhstack:
                    dropit = False
            if dropit:
                stmts.append(table.drop())
            else:
                inhstack.insert(0, table)
        for (sch, tbl) in self:
            table = self[(sch, tbl)]
            if isinstance(table, Sequence) \
                    and hasattr(table, 'dependent_table') \
                    and hasattr(table, 'dropped') and not table.dropped:
                stmts.append(table.drop())

        # last pass to deal with nextval DEFAULTs
        for (sch, tbl) in intables:
            intable = intables[(sch, tbl)]
            if not isinstance(intable, Table):
                continue
            if (sch, tbl) not in self:
                for col in intable.columns:
                    if hasattr(col, 'default') \
                            and col.default.startswith('nextval'):
                        stmts.append(col.set_sequence_default())

        return stmts
