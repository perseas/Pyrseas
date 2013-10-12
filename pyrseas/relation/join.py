# -*- coding: utf-8 -*-
"""
    pyrseas.relation.join
"""
from pyrseas.relation.attribute import Attribute
from pyrseas.relation.tuple import Tuple


class ProjAttribute(Attribute):

    def __init__(self, name, type_=str, value=None, nullable=False,
                 sysdefault=False, basename=None, projection=None):
        super(ProjAttribute, self).__init__(name, type_, value, nullable,
                                            sysdefault)
        self.basename = basename or self.name
        self.projection = projection


class Projection(object):
    "A relational projection, from a single relvar"

    def __init__(self, rvname, attribs, rangevar=None):
        """Initialize a relational projection

        :param rvname: relvar name
        :param attribs: list of Attributes
        :param rangevar: range variable for relvar
        """
        self.rvname = rvname
        self.attributes = tuple([(attr.name, attr) for attr in attribs])
        self.rangevar = rangevar or rvname[0]


class JoinRelation(object):
    "A join of one or more projected relations"

    def __init__(self, projlist, join=None, extname=None):
        attribs = []
        rangevars = []
        for proj in projlist:
            if proj.rangevar in rangevars:
                raise ValueError("Duplicate rangevar '%s'" % proj.rangevar)
            rangevars.append(proj.rangevar)
            for (name, attr) in proj.attributes:
                if name not in attribs:
                    attr.projection = proj
                    attribs.append(attr)
        self.attributes = tuple([(attr.name, attr) for attr in attribs])
        self._required_attribs = [name for name, attr in self.attributes
                                  if (not attr.sysdefault and
                                      not attr.nullable)]
        name = projlist[0].rvname
        if extname is None:
            self.extname = name
        else:
            self.extname = extname
        self.from_clause = "%s %s" % (name, projlist[0].rangevar)
        if len(projlist) > 1:
            assert join is not None, "Must provide 'join' clause"
        if join:
            self.from_clause += " %s" % (join)

    def connect(self, dbconn):
        """Specify the database where the relations are present

        :param dbconn: DbConnection object
        """
        self.db = dbconn

    def tuple(self, *args, **kwargs):
        """Return a Tuple based on relation and passed-in arguments

        :param args: positional arguments corresponding to attributes
        :param kwargs: keyword arguments corresponding to attributes
        :return: Tuple
        """
        kwargs.update(dict(list(zip([name for name, attr in self.attributes],
                                    args))))
        attribs = []
        namelist = []
        attrs = dict(self.attributes)
        for (argname, argval) in list(kwargs.items()):
            attr = attrs[argname]
            attribs.append(Attribute(
                argname, attr.type, argval, nullable=attr.nullable,
                sysdefault=attr.sysdefault))
            namelist.append(argname)
        for name, attr in self.attributes:
            if name not in namelist and name in self._required_attribs:
                attribs.append(Attribute(name, attr.type,
                                         nullable=attr.nullable,
                                         sysdefault=attr.sysdefault))
        return Tuple(attribs)

    def where_clause(self, qry_args=None):
        if not qry_args:
            return ('', {})
        attrs = {}
        for name, attr in self.attributes:
            if attr.name != attr.basename:
                expr = "%s.%s" % (attr.projection.rangevar, attr.basename)
            else:
                expr = "%s.%s" % (attr.projection.rangevar, attr.name)
            attrs.update({attr.name: (expr, attr.type)})
        subclauses = []
        params = {}
        for name in qry_args:
            if name not in attrs:
                raise KeyError("Attribute '%s' not allowed in query string" %
                               name)
            (expr, type_) = attrs[name]
            if type_ == str:
                subclauses.append("%s ILIKE %%(%s)s" % (expr, name))
                params.update({name: '%%%s%%' % qry_args[name]})
            else:
                arg = qry_args[name].strip()
                oper = '='
                if arg[:2] in ['>=', '!=', '<=']:
                    oper = arg[:2]
                    arg = arg[2:].strip()
                elif arg[:1] in ['>', '<']:
                    oper = arg[:1]
                    arg = arg[1:].strip()
                subclauses.append("%s %s %%(%s)s" % (expr, oper, name))
                if type_ in (int, float):
                    arg = type_(arg)
                params.update({name: arg})

        return (" WHERE %s" % " AND ".join(subclauses), params)

    def count(self, qry_args=None):
        """Execute a COUNT() possibly based on a WHERE clause

        :param qry_args: query arguments to form WHERE clause
        :return: integer result from COUNT()
        """
        (where, params) = self.where_clause(qry_args)
        row = self.db.fetchone(
            "SELECT COUNT(*) FROM " + self.from_clause + where, params)
        self.db.rollback()
        return row[0]

    def subset(self, limit='ALL', offset=0, qry_args='', order=[]):
        """Execute a multiple-tuple retrieval and return the tuple data

        :param limit: literal 'ALL' or integer, max tuples to return
        :param offset: integer, offset into subset
        :param qry_args: dictionary of query arguments
        :param order: list of attributes to sort on, possibly including DESC
        :return: list of tuples
        """
        (where, params) = self.where_clause(qry_args)

        def getsubset_qry():
            if not hasattr(self, 'getsubset_qry'):
                exprs = []
                for name, attr in self.attributes:
                    if attr.name != attr.basename:
                        exprs.append("%s.%s AS %s" % (
                            attr.projection.rangevar, attr.basename,
                            attr.name))
                    else:
                        exprs.append("%s.%s" % (attr.projection.rangevar,
                                                attr.name))
                self.getsubset_qry = "SELECT %s FROM %s" % (
                    ", ".join(exprs), self.from_clause)
            return self.getsubset_qry

        slice_ = " LIMIT %s OFFSET %d" % (limit, offset)
        orderby = " ORDER BY 1"
        if order:
            attrnames = [name for (name, attr) in self.attributes]
            for name in order:
                nm = name.rstrip()
                if nm[-5:].upper() == ' DESC':
                    nm = nm[:-5]
                elif nm[-4:].upper() == ' ASC':
                    nm = nm[:-4]
                if nm not in attrnames:
                    raise AttributeError("JoinRelation %s has no attribute "
                                         "'%s'" % (self.extname, nm))
            orderby = " ORDER BY %s" % ", ".join(order)
        query = getsubset_qry() + where + orderby + slice_
        rows = self.db.fetchall(query, params)
        self.db.rollback()
        return [self.tuple(**row) for row in rows]
