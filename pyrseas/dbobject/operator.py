# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.operator
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: Operator derived from
    DbSchemaObject and OperatorDict derived from DbObjectDict.
"""
from . import DbObjectDict, DbSchemaObject
from . import quote_id, commentable, ownable
from . import split_schema_obj, split_func_args


class Operator(DbSchemaObject):
    """An operator"""

    keylist = ['schema', 'name', 'leftarg', 'rightarg']
    single_extern_file = True
    catalog = 'pg_operator'

    def __init__(self, name, schema, description, owner, procedure,
                 leftarg=None, rightarg=None, commutator=None, negator=None,
                 restrict=None, join=None, hashes=False, merges=False,
                 oid=None):
        """Initialize the operator

        :param name: operator name (from oprname)
        :param description: comment text (from obj_description())
        :param schema: schema name (from oprnamespace)
        :param owner: owner name (from rolname via oprowner)
        :param procedure: implementor function (from oprcode)
        :param leftarg: left operand type (from oprleft)
        :param rightarg: right operand type (from oprright)
        :param commutator: commutator, if any (from oprcom)
        :param negator: negator, if any (from oprnegate)
        :param restrict: restriction selectivity function (from oprrest)
        :param join: join selectivity function (from oprjoin)
        :param hashes: supports hash joins? (from oprcanhash)
        :param merges: support merge joins? (from oprcanmerge)
        """
        super(Operator, self).__init__(name, schema, description)
        self._init_own_privs(owner, [])
        self.procedure = procedure
        self.leftarg = leftarg if leftarg != '-' else None
        self.rightarg = rightarg if rightarg != '-' else None
        self.commutator = commutator if commutator != '0' else None
        self.negator = negator if negator != '0' else None
        self.restrict = restrict if restrict != '-' else None
        self.join = join if join != '-' else None
        self.hashes = hashes
        self.merges = merges
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT nspname AS schema, oprname AS name, rolname AS owner,
                   oprleft::regtype AS leftarg, oprright::regtype AS rightarg,
                   oprcode AS procedure, oprcom::regoper AS commutator,
                   oprnegate::regoper AS negator, oprrest AS restrict,
                   oprjoin AS join, oprcanhash AS hashes,
                   oprcanmerge AS merges,
                   obj_description(o.oid, 'pg_operator') AS description, o.oid
            FROM pg_operator o JOIN pg_roles r ON (r.oid = oprowner)
                 JOIN pg_namespace n ON (oprnamespace = n.oid)
            WHERE (nspname != 'pg_catalog' AND nspname != 'information_schema')
              AND o.oid NOT IN (
                  SELECT objid FROM pg_depend WHERE deptype = 'e'
                               AND classid = 'pg_operator'::regclass)
            ORDER BY nspname, oprname"""

    @staticmethod
    def from_map(name, schema, leftarg, rightarg, inobj):
        """Initialize an operator instance from a YAML map

        :param name: operator name
        :param name: schema name
        :param leftarg: left-hand argument
        :param rightarg: right-hand argument
        :param inobj: YAML map of the operator
        :return: operator instance
        """
        obj = Operator(
            name, schema.name, inobj.pop('description', None),
            inobj.pop('owner', None), inobj.pop('procedure', None),
            leftarg, rightarg, inobj.pop('commutator', None),
            inobj.pop('negator', None), inobj.pop('restrict', None),
            inobj.pop('join', None), inobj.pop('hashes', False),
            inobj.pop('merges', None))
        obj.set_oldname(inobj)
        return obj

    def extern_key(self):
        """Return the key to be used in external maps for this operator

        :return: string
        """
        return '%s %s(%s, %s)' % (
            self.objtype.lower(), self.name,
            'NONE' if self.leftarg is None else self.leftarg,
            'NONE' if self.rightarg is None else self.rightarg)

    def qualname(self):
        """Return the schema-qualified name of the operator

        :return: string

        No qualification is used if the schema is 'public'.
        """
        return self.schema == 'public' and self.name \
            or "%s.%s" % (quote_id(self.schema), self.name)

    def identifier(self):
        """Return a full identifier for an operator object

        :return: string
        """
        return "%s(%s, %s)" % (self.qualname(), self.leftarg, self.rightarg)

    def to_map(self, db, no_owner=False):
        """Convert an operator to a YAML-suitable format

        :param db: db used to tie the objects together
        :param no_owner: exclude object owner information
        :return: dictionary
        """
        dct = super(Operator, self).to_map(db, no_owner)
        for attr in ['commutator', 'join', 'negator', 'restrict']:
            if dct[attr] is None:
                dct.pop(attr)
        for attr in ['hashes', 'merges']:
            if dct[attr] is False:
                dct.pop(attr)
        return dct

    @commentable
    @ownable
    def create(self, dbversion=None):
        """Return SQL statements to CREATE or REPLACE the operator

        :return: SQL statements
        """
        opt_clauses = []
        if self.leftarg is not None:
            opt_clauses.append("LEFTARG = %s" % self.leftarg)
        if self.rightarg is not None:
            opt_clauses.append("RIGHTARG = %s" % self.rightarg)
        if self.commutator is not None:
            opt_clauses.append("COMMUTATOR = OPERATOR(%s)" % self.commutator)
        if self.negator is not None:
            opt_clauses.append("NEGATOR = OPERATOR(%s)" % self.negator)
        if self.restrict is not None:
            opt_clauses.append("RESTRICT = %s" % self.restrict)
        if self.join is not None:
            opt_clauses.append("JOIN = %s" % self.join)
        if self.hashes:
            opt_clauses.append("HASHES")
        if self.merges:
            opt_clauses.append("MERGES")
        return ["CREATE OPERATOR %s (\n    PROCEDURE = %s%s%s)" % (
                self.qualname(), self.procedure,
                ',\n    ' if opt_clauses else '', ',\n    '.join(opt_clauses))]

    def get_implied_deps(self, db):
        deps = super(Operator, self).get_implied_deps(db)

        # Types may be not found because builtin, or the operator unary
        if self.leftarg is not None:
            leftarg = db.types.find(self.leftarg)
            if leftarg:
                deps.add(leftarg)

        if self.rightarg is not None:
            rightarg = db.types.find(self.rightarg)
            if rightarg:
                deps.add(rightarg)

        # The function instead we expect it exists
        # TODO: another ugly hack to locate the object
        fschema, fname = split_schema_obj(self.procedure, self.schema)
        fargs = ', '.join(t for t in [self.leftarg, self.rightarg]
                          if t is not None)
        if (fschema, fname, fargs) in db.functions:
            func = db.functions[fschema, fname, fargs]
            deps.add(func)

        # This helper function may be a builtin
        if self.restrict is not None:
            fschema, fname = split_schema_obj(self.restrict)
            func = db.functions.get((fschema, fname,
                                    "internal, oid, internal, integer"))
            if func:
                deps.add(func)

        return deps


class OperatorDict(DbObjectDict):
    "The collection of operators in a database"

    cls = Operator

    def find(self, oper):
        """Return an operator given its signature

        :param oper: a signature such as '#>=#(hstore,hstore)'

        Return the operator found, else None.
        """
        schema, name = split_schema_obj(oper)
        name, args = split_func_args(name)
        return self.get((schema, name) + tuple(args))

    def from_map(self, schema, inopers):
        """Initialize the dictionary of operators by converting the input map

        :param schema: schema owning the operators
        :param inopers: YAML map defining the operators
        """
        for key in inopers:
            (objtype, spc, opr) = key.partition(' ')
            if spc != ' ' or objtype != 'operator':
                raise KeyError("Unrecognized object type: %s" % key)
            paren = opr.find('(')
            if paren == -1 or opr[-1:] != ')':
                raise KeyError("Invalid operator signature: %s" % opr)
            (leftarg, rightarg) = opr[paren + 1:-1].split(',')
            if leftarg == 'NONE':
                leftarg = None
            rightarg = rightarg.lstrip()
            if rightarg == 'NONE':
                rightarg = None
            inobj = inopers[key]
            opr = opr[:paren]
            self[(schema.name, opr, leftarg, rightarg)] = Operator.from_map(
                opr, schema, leftarg, rightarg, inobj)
