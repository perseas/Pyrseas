# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.cast
    ~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: Cast derived from DbObject and
    CastDict derived from DbObjectDict.
"""
from . import DbObject, DbObjectDict, commentable
from . import split_func_args


CONTEXTS = {'a': 'assignment', 'e': 'explicit', 'i': 'implicit'}
METHODS = {'f': 'function', 'i': 'inout', 'b': 'binary coercible'}


class Cast(DbObject):
    """A cast from a source type to a target type"""

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
        if len(context) == 1:
            self.context = CONTEXTS[context]
        else:
            self.context = context
        if len(method) == 1:
            self.method = METHODS[method]
        else:
            self.method = method
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        return """
            SELECT castsource::regtype AS source,
                   casttarget::regtype AS target,
                   CASE WHEN castmethod = 'f' THEN castfunc::regprocedure
                        ELSE NULL::regprocedure END AS function,
                   castcontext AS context, castmethod AS method,
                   obj_description(c.oid, 'pg_cast') AS description, c.oid
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

    @staticmethod
    def from_map(source, target, inobj):
        """Initialize a Cast instance from a YAML map

        :param source: source type name
        :param target: target type name
        :param inobj: YAML map of the cast
        :return: cast instance
        """
        return Cast(
            source, target, inobj.pop('description', None),
            inobj.pop('function', None), inobj.get('context'),
            inobj.get('method'))

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
        dct = super(Cast, self).to_map(db)
        del dct['name']
        if self.function is None:
            del dct['function']
        return dct

    @commentable
    def create(self, dbversion=None):
        """Return SQL statements to CREATE the cast

        :return: SQL statements
        """
        with_clause = "\n    WITH"
        if self.function is not None:
            with_clause += " FUNCTION %s" % self.function
        elif self.method == 'inout':
            with_clause += " INOUT"
        else:
            with_clause += "OUT FUNCTION"
        as_clause = ''
        if self.context == 'assignment':
            as_clause = "\n    AS ASSIGNMENT"
        elif self.context == 'implicit':
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
        if self.method == 'function':
            f = db.functions.find(*split_func_args(self.function))
            if f is not None:
                deps.add(f)

        return deps


class CastDict(DbObjectDict):
    "The collection of casts in a database"

    cls = Cast

    def from_map(self, incasts, newdb):
        """Initialize the dictionary of casts by converting the input map

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
            inobj = incasts[key]
            if not inobj:
                raise ValueError("Cast '%s' has no specification" % key[5:])
            self[(src, trg)] = Cast.from_map(src, trg, inobj)
