# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.view
    ~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: View derived from DbClass and
    MaterializedView derived from View.
"""
from pyrseas.yamlutil import MultiLineStr
from . import commentable, ownable, grantable
from .table import DbClass
from .column import Column


class View(DbClass):
    """A database view definition

    A view is identified by its schema name and view name.
    """
    def __init__(self, name, schema, description, owner, privileges,
                 definition,
                 oid=None):
        """Initialize the view

        :param name-privileges: see DbClass.__init__ params
        :param definition: prettified definition (from pg_getviewdef)
        """
        super(View, self).__init__(name, schema, description, owner,
                                   privileges)
        self.definition = MultiLineStr(definition)
        self.triggers = {}
        self.columns = []
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT nspname AS schema, relname AS name, rolname AS owner,
                   array_to_string(relacl, ',') AS privileges,
                   pg_get_viewdef(c.oid, TRUE) AS definition,
                   obj_description(c.oid, 'pg_class') AS description, c.oid
            FROM pg_class c JOIN pg_roles r ON (r.oid = relowner)
                 JOIN pg_namespace ON (relnamespace = pg_namespace.oid)
            WHERE relkind = 'v'
              AND nspname != 'pg_catalog' AND nspname != 'information_schema'
            ORDER BY nspname, relname"""

    @staticmethod
    def from_map(name, schema, inobj):
        """Initialize a view instance from a YAML map

        :param name: view name
        :param name: schema map
        :param inobj: YAML map of the view
        :return: view instance
        """
        obj = View(
            name, schema.name, inobj.pop('description', None),
            inobj.pop('owner', None), inobj.pop('privileges', []),
            inobj.pop('definition', None))
        if "columns" in inobj:
            obj.columns = [Column(list(col.keys())[0], schema.name, name,
                                  i + 1,
                                  list(col.values())[0].get("type", None))
                           for i, col in enumerate(inobj.get("columns"))]
        if 'depends_on' in inobj:
            obj.depends_on.extend(inobj['depends_on'])
        obj.fix_privileges()
        obj.set_oldname(inobj)
        return obj

    privobjtype = "TABLE"

    @property
    def allprivs(self):
        return 'arwdDxt'

    def to_map(self, db, opts):
        """Convert a view to a YAML-suitable format

        :param opts: options to include/exclude tables, etc.
        :return: dictionary
        """
        if hasattr(opts, 'excl_tables') and opts.excl_tables \
                and self.name in opts.excl_tables:
            return None
        dct = super(View, self).to_map(db, opts.no_owner, opts.no_privs)
        dct['columns'] = [col.to_map(db, opts.no_privs)
                          for col in self.columns]
        if 'dependent_funcs' in dct:
             dct.pop('dependent_funcs')
        if len(self.triggers) > 0:
            for key in list(self.triggers.values()):
                dct['triggers'].update(self.triggers[key.name].to_map(db))
        else:
            dct.pop('triggers')
        return dct

    @commentable
    @grantable
    @ownable
    def create(self, dbversion=None, newdefn=None):
        """Return SQL statements to CREATE the view

        :return: SQL statements
        """
        defn = newdefn or self.definition
        if defn[-1:] == ';':
            defn = defn[:-1]
        return ["CREATE%s VIEW %s AS\n   %s" % (
                newdefn and " OR REPLACE" or '', self.qualname(), defn)]

    def alter(self, inview, dbversion=None):
        """Generate SQL to transform an existing view

        :param inview: a YAML map defining the new view
        :return: list of SQL statements

        Compares the view to an input view and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []
        for col in self.columns:
            if col.name != inview.columns[col.number - 1].name:
                raise KeyError("Cannot change name of view column '%s'"
                                % col.name)
            if col.type != inview.columns[col.number - 1].type:
                raise TypeError("Cannot change datatype of view column '%s'"
                                % col.name)
        if self.definition != inview.definition:
            stmts.append(self.create(dbversion, inview.definition))
        stmts.append(super(View, self).alter(inview))
        return stmts


class MaterializedView(View):
    """A materialized view definition

    A materialized view is identified by its schema name and view name.
    """
    def __init__(self, name, schema, description, owner, privileges,
                 definition, with_data=False,
                 oid=None):
        """Initialize the materialized view

        :param name-privileges: see DbClass.__init__ params
        :param definition: prettified definition (from pg_getviewdef)
        :param with_data: is view populated (from relispopulated)
        """
        super(MaterializedView, self).__init__(
            name, schema, description, owner, privileges, definition)
        self.with_data = with_data
        self.indexes = {}
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT nspname AS schema, relname AS name, rolname AS owner,
                   array_to_string(relacl, ',') AS privileges,
                   pg_get_viewdef(c.oid, TRUE) AS definition,
                   relispopulated AS with_data,
                   obj_description(c.oid, 'pg_class') AS description, c.oid
            FROM pg_class c JOIN pg_roles r ON (r.oid = relowner)
                 JOIN pg_namespace ON (relnamespace = pg_namespace.oid)
            WHERE relkind = 'm'
              AND nspname != 'pg_catalog' AND nspname != 'information_schema'
            ORDER BY nspname, relname"""

    @staticmethod
    def from_map(name, schema, inobj):
        """Initialize a materialized view instance from a YAML map

        :param name: view name
        :param name: schema map
        :param inobj: YAML map of the view
        :return: materialized view instance
        """
        obj = MaterializedView(
            name, schema.name, inobj.pop('description', None),
            inobj.pop('owner', None), inobj.pop('privileges', []),
            inobj.pop('definition', None))
        if "columns" in inobj:
            obj.columns = [Column(list(col.keys())[0], schema.name, name,
                                  i + 1,
                                  list(col.values())[0].get("type", None))
                           for i, col in enumerate(inobj.get("columns"))]
        obj.fix_privileges()
        obj.set_oldname(inobj)
        return obj

    @property
    def objtype(self):
        return "MATERIALIZED VIEW"

    def to_map(self, db, opts):
        """Convert a materialized view to a YAML-suitable format

        :param opts: options to include/exclude tables, etc.
        :return: dictionary
        """
        if hasattr(opts, 'excl_tables') and opts.excl_tables \
                and self.name in opts.excl_tables:
            return None
        mvw = super(MaterializedView, self).to_map(db, opts)
        if len(self.indexes) > 0:
            for k in list(self.indexes.values()):
                mvw['indexes'].update(self.indexes[k.name].to_map(db))
        else:
            mvw.pop('indexes')
        return mvw

    @commentable
    @grantable
    @ownable
    def create(self, dbversion=None, newdefn=None):
        """Return SQL statements to CREATE the materialized view

        :return: SQL statements
        """
        defn = newdefn or self.definition
        if defn[-1:] == ';':
            defn = defn[:-1]
        return ["CREATE %s %s AS\n   %s" % (
                self.objtype, self.qualname(), defn)]
