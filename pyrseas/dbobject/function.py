# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.function
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    This module defines four classes: Proc derived from
    DbSchemaObject, Function and Aggregate derived from Proc, and
    FunctionDict derived from DbObjectDict.
"""
from pyrseas.yamlutil import MultiLineStr
from . import DbObjectDict, DbSchemaObject
from . import commentable, ownable, grantable, split_schema_obj

VOLATILITY_TYPES = {'i': 'immutable', 's': 'stable', 'v': 'volatile'}
PARALLEL_SAFETY = {'r': 'restricted', 's': 'safe', 'u': 'unsafe'}


def split_schema_func(schema, func):
    """Split a function related to an object from its schema

    :param schema: schema to which the main object belongs
    :param func: possibly qualified function name
    :returns: a schema, function tuple, or just the unqualified function name
    """
    (sch, fnc) = split_schema_obj(func, schema)
    if sch != schema:
        return (sch, fnc)
    else:
        return fnc


def join_schema_func(func):
    """Join the schema and function, if needed, to form a qualified name

    :param func: a schema, function tuple, or just an unqualified function name
    :returns: a possibly-qualified schema.function string
    """
    if isinstance(func, tuple):
        return "%s.%s" % func
    else:
        return func


class Proc(DbSchemaObject):
    """A procedure such as a FUNCTION or an AGGREGATE"""

    keylist = ['schema', 'name', 'arguments']
    catalog = 'pg_proc'

    @property
    def allprivs(self):
        return 'X'

    def __init__(self, name, schema, description, owner, privileges,
                 arguments):
        """Initialize the procedure

        :param name: function name (from proname)
        :param schema: schema name (from pronamespace)
        :param description: comment text (from obj_description())
        :param owner: owner name (from rolname via proowner)
        :param privileges: access privileges (from proacl)
        :param arguments: argument list (without default values, from
               pg_function_identity_arguments)
        """
        super(Proc, self).__init__(name, schema, description)
        self._init_own_privs(owner, privileges)
        self.arguments = arguments

    def extern_key(self):
        """Return the key to be used in external maps for this function

        :return: string
        """
        return '%s %s(%s)' % (self.objtype.lower(), self.name, self.arguments)

    def identifier(self):
        """Return a full identifier for a function object

        :return: string
        """
        return "%s(%s)" % (self.qualname(), self.arguments)

    def get_implied_deps(self, db):
        # List the previous dependencies
        deps = super(Proc, self).get_implied_deps(db)

        # Add back the language
        if isinstance(self, Function) and getattr(self, 'language', None):
            lang = db.languages.get(self.language)
            if lang:
                deps.add(lang)

        # Add back the types
        if self.arguments:
            for arg in self.arguments.split(', '):
                arg = db.find_type(arg.split()[-1])
                if arg is not None:
                    deps.add(arg)

        return deps


class Function(Proc):
    """A procedural language function"""

    def __init__(self, name, schema, description, owner, privileges,
                 arguments, language, returns, source, obj_file=None,
                 configuration=None, volatility=None, leakproof=False,
                 strict=False, security_definer=False, cost=0, rows=0,
                 allargs=None, oid=None):
        """Initialize the function

        :param name-arguments: see Proc.__init__ params
        :param language: implementation language (from prolang)
        :param returns: return type (from pg_get_function_result/prorettype)
        :param source: source code, link symbol, etc. (from prosrc)
        :param obj_file: language-specific info (from probin)
        :param configuration: configuration variables (from proconfig)
        :param volatility: volatility type (from provolatile)
        :param leakproof: has side effects (from proleakproof)
        :param strict: null handling (from proisstrict)
        :param security_definer: security definer (from prosecdef)
        :param cost: execution cost estimate (from procost)
        :param rows: result row estimate (from prorows)
        :param allargs: argument list with defaults (from
               pg_get_function_arguments)
        """
        super(Function, self).__init__(
            name, schema, description, owner, privileges, arguments)
        self.language = language
        self.returns = returns
        if source and '\n' in source:
            newsrc = []
            for line in source.split('\n'):
                if line and line[-1] in (' ', '\t'):
                    line = line.rstrip()
                newsrc.append(line)
            source = '\n'.join(newsrc)
        self.source = MultiLineStr(source)
        self.obj_file = obj_file
        self.configuration = configuration
        self.allargs = allargs
        if volatility is not None:
            self.volatility = volatility[:1].lower()
        else:
            self.volatility = 'v'
        assert self.volatility in VOLATILITY_TYPES.keys()
        self.leakproof = leakproof
        self.strict = strict
        self.security_definer = security_definer
        self.cost = cost
        self.rows = rows
        self.oid = oid

    @staticmethod
    def query(dbversion=None):
        query = """
            SELECT nspname AS schema, proname AS name,
                   pg_get_function_identity_arguments(p.oid) AS arguments,
                   pg_get_function_arguments(p.oid) AS allargs,
                   pg_get_function_result(p.oid) AS returns, rolname AS owner,
                   array_to_string(proacl, ',') AS privileges,
                   l.lanname AS language, provolatile AS volatility,
                   proisstrict AS strict, prosrc AS source,
                   probin::text AS obj_file, proconfig AS configuration,
                   prosecdef AS security_definer, procost AS cost,
                   proleakproof AS leakproof, prorows::integer AS rows,
                   obj_description(p.oid, 'pg_proc') AS description, p.oid
            FROM pg_proc p JOIN pg_roles r ON (r.oid = proowner)
                 JOIN pg_namespace n ON (pronamespace = n.oid)
                 JOIN pg_language l ON (prolang = l.oid)
            WHERE (nspname != 'pg_catalog' AND nspname != 'information_schema')
              AND %s
              AND p.oid NOT IN (
                  SELECT objid FROM pg_depend WHERE deptype = 'e'
                               AND classid = 'pg_proc'::regclass)
            ORDER BY nspname, proname"""
        if dbversion < 110000:
            query = query % "NOT proisagg"
        else:
            query = query % "prokind = 'f'"
        return query

    @staticmethod
    def from_map(name, schema, arguments, inobj):
        """Initialize a function instance from a YAML map

        :param name: function name
        :param name: schema name
        :param arguments: arguments
        :param inobj: YAML map of the function
        :return: function instance
        """
        src = inobj.get('source', None)
        objfile = inobj.get('obj_file', None)
        if (src and objfile) or not (src or objfile):
            raise ValueError("Function '%s': either source or obj_file must "
                             "be specified" % name)
        obj = Function(
            name, schema.name, inobj.pop('description', None),
            inobj.pop('owner', None), inobj.pop('privileges', []),
            arguments, inobj.pop('language', None),
            inobj.pop('returns', None), inobj.pop('source', None),
            inobj.pop('obj_file', None),
            inobj.pop('configuration', None),
            inobj.pop('volatility', None),
            inobj.pop('leakproof', False), inobj.pop('strict', False),
            inobj.pop('security_definer', False),
            inobj.pop('cost', 0), inobj.pop('rows', 0),
            inobj.pop('allargs', None))
        obj.fix_privileges()
        return obj

    def to_map(self, db, no_owner, no_privs):
        """Convert a function to a YAML-suitable format

        :param no_owner: exclude function owner information
        :param no_privs: exclude privilege information
        :return: dictionary
        """
        dct = super(Function, self).to_map(db, no_owner, no_privs)
        for attr in ('leakproof', 'strict', 'security_definer'):
            if dct[attr] is False:
                dct.pop(attr)
        if self.allargs is None or len(self.allargs) == 0 or \
           self.allargs == self.arguments:
            dct.pop('allargs')
        if self.configuration is None:
            dct.pop('configuration')
        if self.volatility == 'v':
            dct.pop('volatility')
        else:
            dct['volatility'] = VOLATILITY_TYPES[self.volatility]
        if self.obj_file is not None:
            dct['link_symbol'] = self.source
            del dct['source']
        else:
            del dct['obj_file']
        if self.cost != 0:
            if self.language in ['c', 'internal']:
                if self.cost == 1:
                    del dct['cost']
            else:
                if self.cost == 100:
                    del dct['cost']
        else:
            del dct['cost']
        if self.rows != 0:
            if self.rows == 1000:
                del dct['rows']
        else:
            del dct['rows']

        return dct

    @commentable
    @grantable
    @ownable
    def create(self, dbversion=None, newsrc=None, basetype=False, returns=None):
        """Return SQL statements to CREATE or REPLACE the function

        :param newsrc: new source for a changed function
        :return: SQL statements
        """
        stmts = []
        if self.obj_file is not None:
            src = "'%s', '%s'" % (self.obj_file,
                                  hasattr(self, 'link_symbol') and
                                  self.link_symbol or self.name)
        elif self.language == 'internal':
            src = "$$%s$$" % (newsrc or self.source)
        else:
            src = "$_$%s$_$" % (newsrc or self.source)
        volat = leakproof = strict = secdef = cost = rows = config = ''
        if self.volatility != 'v':
            volat = ' ' + VOLATILITY_TYPES[self.volatility].upper()
        if self.leakproof is True:
            leakproof = ' LEAKPROOF'
        if self.strict:
            strict = ' STRICT'
        if self.security_definer:
            secdef = ' SECURITY DEFINER'
        if self.configuration is not None:
            config = ' SET %s' % self.configuration[0]
        if self.cost != 0:
            if self.language in ['c', 'internal']:
                if self.cost != 1:
                    cost = " COST %s" % self.cost
            else:
                if self.cost != 100:
                    cost = " COST %s" % self.cost
        if self.rows != 0:
            if self.rows != 1000:
                rows = " ROWS %s" % self.rows

        # We may have to create a shell type if we are its input or output
        # functions
        t = getattr(self, '_defining', None)
        if t is not None:
            if not hasattr(t, '_shell_created'):
                t._shell_created = True
                stmts.append("CREATE TYPE %s" % t.qualname())

        if self.allargs is not None:
            args = self.allargs
        elif self.arguments is not None:
            args = self.arguments
        else:
            args = ''
        stmts.append("CREATE%s FUNCTION %s(%s) RETURNS %s\n    LANGUAGE %s"
                     "%s%s%s%s%s%s%s\n    AS %s" % (
                         newsrc and " OR REPLACE" or '', self.qualname(),
                         args, returns or self.returns, self.language, volat, leakproof,
                         strict, secdef, cost, rows, config, src))
        return stmts

    def alter(self, infunction, dbversion=None, no_owner=False):
        """Generate SQL to transform an existing function

        :param infunction: a YAML map defining the new function
        :return: list of SQL statements

        Compares the function to an input function and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []
        if self.source != infunction.source and infunction.source is not None:
            stmts.append(self.create(
                dbversion=dbversion,
                returns=infunction.returns,
                newsrc=infunction.source,
            ))
        if self.leakproof is True:
            if infunction.leakproof is True:
                stmts.append("ALTER FUNCTION %s LEAKPROOF" % self.identifier())
            else:
                stmts.append("ALTER FUNCTION %s NOT LEAKPROOF"
                             % self.identifier())
        elif infunction.leakproof is True:
            stmts.append("ALTER FUNCTION %s LEAKPROOF" % self.qualname())
        stmts.append(super(Function, self).alter(infunction,
                                                 no_owner=no_owner))
        return stmts

    def get_implied_deps(self, db):
        # List the previous dependencies
        deps = super(Function, self).get_implied_deps(db)

        # Add back the return type
        rettype = self.returns
        if rettype.upper().startswith("SETOF "):
            rettype = rettype.split(None, 1)[-1]
        rettype = db.find_type(rettype)
        if rettype is not None:
            deps.add(rettype)

        return deps

    def get_deps(self, db):
        deps = super(Function, self).get_deps(db)

        # avoid circular import dependencies
        from .dbtype import DbType

        # drop the dependency on the type if this function is an in/out
        # because there is a loop here.
        for dep in list(deps):
            if isinstance(dep, DbType):
                for attr in ('input', 'output', 'send', 'receive'):
                    fname = getattr(dep, attr, None)
                    if isinstance(fname, tuple):
                        fname = "%s.%s" % fname
                    else:
                        fname = "%s.%s" % (self.schema, fname)
                    if fname and fname == self.qualname():
                        deps.remove(dep)
                        self._defining = dep    # we may need a shell for this
                        break

        return deps

    def drop(self):
        """Generate SQL to drop the current function

        :return: list of SQL statements
        """
        # If the function defines a type it will be dropped by the CASCADE
        # on the type.
        if getattr(self, '_defining', None):
            return []
        else:
            return super(Function, self).drop()


AGGREGATE_KINDS = {'n': 'normal', 'o': 'ordered', 'h': 'hypothetical'}


class Aggregate(Proc):
    """An aggregate function"""

    def __init__(self, name, schema, description, owner, privileges,
                 arguments, sfunc, stype, sspace=0, finalfunc=None,
                 finalfunc_extra=False, initcond=None, sortop=None,
                 msfunc=None, minvfunc=None, mstype=None, msspace=0,
                 mfinalfunc=None, mfinalfunc_extra=False, minitcond=None,
                 kind='normal', combinefunc=None, serialfunc=None,
                 deserialfunc=None, parallel='unsafe',
                 oid=None):
        """Initialize the aggregate

        :param name-arguments: see Proc.__init__ params
        :param sfunc: state transition function (from aggtransfn)
        :param stype: state datatype (from aggtranstype)
        :param sspace: transition state data size (from aggtransspace)
        :param finalfunc: final function (from aggfinalfn)
        :param finalfunc_extra: extra args? (from aggfinalextra)
        :param initcond: initial value (from agginitval)
        :param sortop: sort operator (from aggsortop)
        :param msfunc: state transition function (from aggmtransfn)
        :param minvfunc: inverse transition function (from aggminvtransfn)
        :param mstype: state datatype (from aggmtranstype)
        :param msspace: transition state data size (from aggmtransspace)
        :param mfinalfunc: final function (from aggfinalfn)
        :param mfinalfunc_extra: extra args? (from aggmfinalextra)
        :param minitcond: initial value (from aggminitval)
        :param kind: aggregate kind (from aggkind)
        :param combinefunc: combine function (from aggcombinefn)
        :param serialfunc: serialization function (from aggserialfn)
        :param deserialfunc: deserialization function (from aggdeserialfn)
        :param parallel: parallel safety indicator (from proparallel)
        """
        super(Aggregate, self).__init__(
            name, schema, description, owner, privileges, arguments)
        self.sfunc = split_schema_obj(sfunc, self.schema)
        self.stype = self.unqualify(stype)
        self.sspace = sspace
        if finalfunc is not None and finalfunc != '-':
            self.finalfunc = split_schema_obj(finalfunc, self.schema)
        else:
            self.finalfunc = None
        self.finalfunc_extra = finalfunc_extra
        self.initcond = initcond
        self.sortop = sortop if sortop != '0' else None
        if msfunc is not None and msfunc != '-':
            self.msfunc = split_schema_obj(msfunc, self.schema)
        else:
            self.msfunc = None
        if minvfunc is not None and minvfunc != '-':
            self.minvfunc = split_schema_obj(minvfunc, self.schema)
        else:
            self.minvfunc = None
        if mstype is not None and mstype != '-':
            self.mstype = self.unqualify(mstype)
        else:
            self.mstype = None
        self.msspace = msspace
        if mfinalfunc is not None and mfinalfunc != '-':
            self.mfinalfunc = split_schema_obj(mfinalfunc, self.schema)
        else:
            self.mfinalfunc = None
        self.mfinalfunc_extra = mfinalfunc_extra
        self.minitcond = minitcond
        if kind is None:
            self.kind = 'normal'
        elif len(kind) == 1:
            self.kind = AGGREGATE_KINDS[kind]
        else:
            self.kind = kind
        assert self.kind in AGGREGATE_KINDS.values()
        self.combinefunc = combinefunc if combinefunc != '-' else None
        self.serialfunc = serialfunc if serialfunc != '-' else None
        self.deserialfunc = deserialfunc if deserialfunc != '-' else None
        if parallel is None:
            self.parallel = 'unsafe'
        elif len(parallel) == 1:
            self.parallel = PARALLEL_SAFETY[parallel]
        else:
            self.parallel = parallel
        assert self.parallel in PARALLEL_SAFETY.values()
        self.oid = oid

    @staticmethod
    def query(dbversion):
        query = """
            SELECT nspname AS schema, proname AS name,
                   pg_get_function_identity_arguments(p.oid) AS arguments,
                   rolname AS owner,
                   array_to_string(proacl, ',') AS privileges,
                   aggtransfn::regproc AS sfunc,
                   aggtranstype::regtype AS stype, aggtransspace AS sspace,
                   aggfinalfn::regproc AS finalfunc,
                   aggfinalextra AS finalfunc_extra,
                   agginitval AS initcond, aggsortop::regoper AS sortop,
                   aggmtransfn::regproc AS msfunc,
                   aggminvtransfn::regproc AS minvfunc,
                   aggmtranstype::regtype AS mstype,
                   aggmtransspace AS msspace,
                   aggmfinalfn::regproc AS mfinalfunc,
                   aggmfinalextra AS mfinalfunc_extra,
                   aggminitval AS minitcond, aggkind AS kind,
                   aggcombinefn AS combinefunc,
                   aggserialfn AS serialfunc, aggdeserialfn AS deserialfunc,
                   proparallel AS parallel,%s
                   obj_description(p.oid, 'pg_proc') AS description, p.oid
            FROM pg_proc p JOIN pg_roles r ON (r.oid = proowner)
                 JOIN pg_namespace n ON (pronamespace = n.oid)
                 LEFT JOIN pg_aggregate a ON (p.oid = aggfnoid)
            WHERE (nspname != 'pg_catalog' AND nspname != 'information_schema')
              %s
              AND p.oid NOT IN (
                  SELECT objid FROM pg_depend WHERE deptype = 'e'
                               AND classid = 'pg_proc'::regclass)
            ORDER BY nspname, proname"""
        extra = ("", "")
        if dbversion < 110000:
            extra = (" proisagg,", "")
        else:
            extra = ("", "AND prokind = 'a'")
        return query % extra

    @staticmethod
    def from_map(name, schema, arguments, inobj):
        """Initialize an aggregate instance from a YAML map

        :param name: aggregate name
        :param name: schema name
        :param arguments: arguments
        :param inobj: YAML map of the aggregate
        :return: aggregate instance
        """
        obj = Aggregate(
            name, schema.name, inobj.pop('description', None),
            inobj.pop('owner', None), inobj.pop('privileges', []),
            arguments, inobj.get('sfunc'), inobj.get('stype'),
            inobj.pop('sspace', 0), inobj.pop('finalfunc', None),
            inobj.pop('finalfunc_extra', False), inobj.pop('initcond', None),
            inobj.pop('sortop', None), inobj.pop('msfunc', None),
            inobj.pop('minvfunc', None), inobj.pop('mstype', None),
            inobj.pop('msspace', 0), inobj.pop('mfinalfunc', None),
            inobj.pop('mfinalfunc_extra', False),
            inobj.pop('minitcond', None), inobj.pop('kind', 'normal'),
            inobj.pop('combinefunc', None), inobj.pop('serialfunc', None),
            inobj.pop('deseriafunc', None), inobj.pop('parallel', 'unsafe'))
        obj.fix_privileges()
        return obj

    def to_map(self, db, no_owner, no_privs):
        """Convert an aggregate to a YAML-suitable format

        :param no_owner: exclude aggregate owner information
        :param no_privs: exclude privilege information
        :return: dictionary
        """
        dct = super(Aggregate, self).to_map(db, no_owner, no_privs)
        dct['sfunc'] = self.unqualify(join_schema_func(self.sfunc))
        for attr in ('finalfunc', 'msfunc', 'minvfunc', 'mfinalfunc'):
            if getattr(self, attr) is None:
                dct.pop(attr)
            else:
                dct[attr] = self.unqualify(
                    join_schema_func(getattr(self, attr)))
        for attr in ('initcond', 'sortop', 'minitcond', 'mstype',
                     'combinefunc', 'serialfunc', 'deserialfunc'):
            if getattr(self, attr) is None:
                dct.pop(attr)
        for attr in ('sspace', 'msspace'):
            if getattr(self, attr) == 0:
                dct.pop(attr)
        for attr in ('finalfunc_extra', 'mfinalfunc_extra'):
            if getattr(self, attr) is False:
                dct.pop(attr)
        if self.kind == 'normal':
            dct.pop('kind')
        if self.parallel == 'unsafe':
            dct.pop('parallel')
        return dct

    @commentable
    @grantable
    @ownable
    def create(self, dbversion=None):
        """Return SQL statements to CREATE the aggregate

        :param dbversion: Posgres version
        :return: SQL statements
        """
        opt_clauses = []
        if self.finalfunc is not None:
            opt_clauses.append("FINALFUNC = %s" %
                               join_schema_func(self.finalfunc))
        if self.initcond is not None:
            opt_clauses.append("INITCOND = '%s'" % self.initcond)
        if self.combinefunc is not None:
            opt_clauses.append("COMBINEFUNC = %s" % self.combinefunc)
        if self.serialfunc is not None:
            opt_clauses.append("SERIALFUNC = %s" % self.serialfunc)
        if self.deserialfunc is not None:
            opt_clauses.append("DESERIALFUNC = %s" % self.deserialfunc)
        if self.sspace > 0:
            opt_clauses.append("SSPACE = %d" % self.sspace)
        if self.finalfunc_extra:
            opt_clauses.append("FINALFUNC_EXTRA")
        if self.msfunc is not None:
            opt_clauses.append("MSFUNC = %s" % join_schema_func(self.msfunc))
        if self.minvfunc is not None:
            opt_clauses.append("MINVFUNC = %s" % join_schema_func(self.minvfunc))
        if self.mstype is not None:
            opt_clauses.append("MSTYPE = %s" % self.mstype)
        if self.msspace > 0:
            opt_clauses.append("MSSPACE = %d" % self.msspace)
        if self.mfinalfunc is not None:
            opt_clauses.append("MFINALFUNC = %s" %
                               join_schema_func(self.mfinalfunc))
        if self.mfinalfunc_extra:
            opt_clauses.append("MFINALFUNC_EXTRA")
        if self.minitcond is not None:
            opt_clauses.append("MINITCOND = '%s'" % self.minitcond)
        if self.kind == 'hypothetical':
            opt_clauses.append("HYPOTHETICAL")
        if self.sortop is not None:
            clause = self.sortop
            if not clause.startswith('OPERATOR'):
                clause = "OPERATOR(%s)" % clause
            opt_clauses.append("SORTOP = %s" % clause)
        if self.parallel != 'unsafe':
            opt_clauses.append("PARALLEL = %s" % self.parallel.upper())
        return ["CREATE AGGREGATE %s(%s) (\n    SFUNC = %s,"
                "\n    STYPE = %s%s%s)" % (
                    self.qualname(), self.arguments,
                    join_schema_func(self.sfunc), self.stype,
                    opt_clauses and ',\n    ' or '',
                    ',\n    '.join(opt_clauses))]

    def get_implied_deps(self, db):
        # List the previous dependencies
        deps = super(Aggregate, self).get_implied_deps(db)

        if isinstance(self.sfunc, tuple):
            sch, fnc = self.sfunc
        else:
            sch, fnc = self.schema, self.sfunc
        if 'ORDER BY' in self.arguments:
            args = self.arguments.replace(' ORDER BY', ',')
        else:
            args = self.stype + ', ' + self.arguments
        deps.add(db.functions[sch, fnc, args])
        for fn in ('finalfunc', 'mfinalfunc'):
            if getattr(self, fn) is not None:
                func = getattr(self, fn)
                if isinstance(func, tuple):
                    sch, fnc = func
                else:
                    sch, fnc = self.schema, func
                deps.add(db.functions[sch, fnc, self.mstype
                                      if fn[0] == 'm' else self.stype])
        for fn in ('msfunc', 'minvfunc'):
            if getattr(self, fn) is not None:
                func = getattr(self, fn)
                if isinstance(func, tuple):
                    sch, fnc = func
                else:
                    sch, fnc = self.schema, func
                args = self.mstype + ", " + self.arguments
                deps.add(db.functions[sch, fnc, args])

        return deps


class ProcDict(DbObjectDict):
    "The collection of regular and aggregate functions in a database"

    cls = Proc

    def _from_catalog(self):
        """Initialize the dictionary of procedures by querying the catalogs"""
        for cls in (Function, Aggregate):
            self.cls = cls
            for obj in self.fetch():
                self[obj.key()] = obj
                self.by_oid[obj.oid] = obj

    def from_map(self, schema, infuncs):
        """Initialize the dictionary of functions by converting the input map

        :param schema: schema owning the functions
        :param infuncs: YAML map defining the functions
        """
        for key in infuncs:
            (objtype, spc, fnc) = key.partition(' ')
            if spc != ' ' or objtype not in ['function', 'aggregate']:
                raise KeyError("Unrecognized object type: %s" % key)
            paren = fnc.find('(')
            if paren == -1 or fnc[-1:] != ')':
                raise KeyError("Invalid function signature: %s" % fnc)
            arguments = fnc[paren + 1:-1]
            inobj = infuncs[key]
            fnc = fnc[:paren]
            if objtype == 'function':
                func = Function.from_map(fnc, schema, arguments, inobj)
            else:
                func = Aggregate.from_map(fnc, schema, arguments, inobj)
            self[(schema.name, fnc, arguments)] = func

    def find(self, func, args):
        """Return a function given its name and arguments

        :param func: name of the function, eventually with schema
        :param args: list of type names

        Return the function found, else None.
        """
        schema, name = split_schema_obj(func)
        args = ', '.join(args)
        return self.get((schema, name, args))

    def link_refs(self, dbtypes):
        """Connect the functions to other objects

        - Connect defining functions to the type they define

        :param dbtypes: dictionary of types
        """
        # TODO: this link is needed from map, not from sql.
        # is this a pattern? I was assuming link_refs would have disappeared
        # but I'm actually still maintaining them. Verify if they are always
        # only used for from_map, not for from_catalog
        for key in dbtypes:
            t = dbtypes[key]
            for f in t.find_defining_funcs(self):
                f._defining = t
