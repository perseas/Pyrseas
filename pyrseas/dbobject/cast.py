# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.cast
    ~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: Cast derived from DbObject and
    CastDict derived from DbObjectDict.
"""
from pyrseas.dbobject import DbObject, DbObjectDict, commentable
from pyrseas.dbobject import split_func_args


CONTEXTS = {'a': 'assignment', 'e': 'explicit', 'i': 'implicit'}
METHODS = {'f': 'function', 'i': 'inout', 'b': 'binary coercible'}


class Cast(DbObject):
    """A cast"""

    keylist = ['source', 'target']
    single_extern_file = True
    catalog = 'pg_cast'

    def __init__(self, source, target, description, function, context, method,
                 oid=None):
        """Initialize the cast

        :param source: source data type (from castsource)
        :param target: target data type (from casttarget)
        :param description: comment text (from obj_description())
        :param function: function to perform the cast (from castfunc)
        :param context: context indicator (from castcontext)
        :param method: method indicator (from castmethod)
        """
        super(Cast, self).__init__('%s AS %s' % (source, target), description)
        self._init_own_privs(None, [])
        self.source = source
        self.target = target
        self.function = function
        self.context = context
        self.method = method
        self.oid = oid

    def extern_key(self):
        """Return the key to be used in external maps for this cast

        :return: string
        """
        return '%s (%s as %s)' % (self.objtype.lower(), self.source,
                                  self.target)

    def identifier(self):
        """Return a full identifier for a cast object

        :return: string
        """
        return "(%s AS %s)" % (self.source, self.target)

    def to_map(self, db, no_owner=False, no_privs=False):
        """Convert a cast to a YAML-suitable format

        :return: dictionary
        """
        dct = self._base_map(db)
        del dct['name']
        if self.function is None:
            del dct['function']
        dct['context'] = CONTEXTS[self.context]
        dct['method'] = METHODS[self.method]
        return dct

    @commentable
    def create(self):
        """Return SQL statements to CREATE the cast

        :return: SQL statements
        """
        with_clause = "\n    WITH"
        if self.function is not None:
            with_clause += " FUNCTION %s" % self.function
        elif self.method == 'i':
            with_clause += " INOUT"
        else:
            with_clause += "OUT FUNCTION"
        as_clause = ''
        if self.context == 'a':
            as_clause = "\n    AS ASSIGNMENT"
        elif self.context == 'i':
            as_clause = "\n    AS IMPLICIT"
        return ["CREATE CAST (%s AS %s)%s%s" % (
                self.source, self.target, with_clause, as_clause)]

    def get_implied_deps(self, db):
        deps = super(Cast, self).get_implied_deps(db)

        # Types may be not found because they can be builtins
        source = db.find_type(self.source)
        if source:
            deps.add(source)

        target = db.find_type(self.target)
        if target:
            deps.add(target)

        # The function instead we expect it exists
        if self.method == 'f':
            f = db.functions.find(*split_func_args(self.function))
            if f is not None:
                deps.add(f)

        return deps


class CastDict(DbObjectDict):
    "The collection of casts in a database"

    cls = Cast
    query = \
        """SELECT c.oid,
                  castsource::regtype AS source,
                  casttarget::regtype AS target,
                  CASE WHEN castmethod = 'f' THEN castfunc::regprocedure
                       ELSE NULL::regprocedure END AS function,
                  castcontext AS context, castmethod AS method,
                  obj_description(c.oid, 'pg_cast') AS description
           FROM pg_cast c
                JOIN pg_type s ON (castsource = s.oid)
                     JOIN pg_namespace sn ON (s.typnamespace = sn.oid)
                JOIN pg_type t ON (casttarget = t.oid)
                     JOIN pg_namespace tn ON (t.typnamespace = tn.oid)
                LEFT JOIN pg_proc p ON (castfunc = p.oid)
                     LEFT JOIN pg_namespace pn ON (p.pronamespace = pn.oid)
           WHERE substring(sn.nspname for 3) != 'pg_'
              OR substring(tn.nspname for 3) != 'pg_'
              OR (castfunc != 0 AND substring(pn.nspname for 3) != 'pg_')
           ORDER BY castsource, casttarget"""

    def from_map(self, incasts, newdb):
        """Initalize the dictionary of casts by converting the input map

        :param incasts: YAML map defining the casts
        :param newdb: collection of dictionaries defining the database
        """
        for key in incasts:
            if not key.startswith('cast (') or ' AS ' not in key.upper() \
                    or key[-1:] != ')':
                raise KeyError("Unrecognized object type: %s" % key)
            asloc = key.upper().find(' AS ')
            src = key[6:asloc]
            trg = key[asloc + 4:-1]
            incast = incasts[key]
            if not incast:
                raise ValueError("Cast '%s' has no specification" % key[5:])
            descr = incast.pop('description', None)
            func = incast.pop('function', None)
            ctxt = incast.pop('context', None)
            meth = incast.pop('method', None)
            if ctxt is None:
                raise ValueError("Cast '%s' missing context" % key[5:])
            ctxt = ctxt[:1].lower()
            if meth is None:
                raise ValueError("Cast '%s' missing method" % key[5:])
            meth = meth[:1].lower()
            self[(src, trg)] = Cast(src, trg, descr, func, ctxt, meth)
