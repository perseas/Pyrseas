# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.view
    ~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: View derived from DbClass and
    MaterializedView derived from View.
"""

from . import commentable, ownable, grantable
from .table import DbClass


class View(DbClass):
    """A database view definition

    A view is identified by its schema name and view name.
    """

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
        view = self._base_map(db, opts.no_owner, opts.no_privs)
        if 'dependent_funcs' in view:
            del view['dependent_funcs']
        if hasattr(self, 'triggers'):
            for key in list(self.triggers.values()):
                view['triggers'].update(self.triggers[key.name].to_map(db))
        return view

    @commentable
    @grantable
    @ownable
    def create(self, newdefn=None):
        """Return SQL statements to CREATE the view

        :return: SQL statements
        """
        defn = newdefn or self.definition
        if defn[-1:] == ';':
            defn = defn[:-1]
        return ["CREATE%s VIEW %s AS\n   %s" % (
                newdefn and " OR REPLACE" or '', self.qualname(), defn)]

    def alter(self, inview):
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
        stmts.append(super(View, self).alter(inview))
        return stmts


class MaterializedView(View):
    """A materialized view definition

    A materialized view is identified by its schema name and view name.
    """

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
        mvw = self._base_map(db, opts.no_owner, opts.no_privs)
        if hasattr(self, 'indexes'):
            if 'indexes' not in mvw:
                mvw['indexes'] = {}
            for k in list(self.indexes.values()):
                mvw['indexes'].update(self.indexes[k.name].to_map(db))
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
