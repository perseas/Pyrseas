# -*- coding: utf-8 -*-
"""
    pyrseas.dbobject.function
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    This module defines four classes: Proc derived from
    DbSchemaObject, Function and Aggregate derived from Proc, and
    FunctionDict derived from DbObjectDict.
"""
from pyrseas.dbobject import DbObjectDict, DbSchemaObject
from pyrseas.dbobject import commentable, ownable, grantable, split_schema_obj
from pyrseas.dbobject.privileges import privileges_from_map

VOLATILITY_TYPES = {'i': 'immutable', 's': 'stable', 'v': 'volatile'}


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
        self.source = source
        self.returns = returns
        self.source = source
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
    def query():
        return """
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
              AND NOT proisagg
              AND p.oid NOT IN (
                  SELECT objid FROM pg_depend WHERE deptype = 'e'
                               AND classid = 'pg_proc'::regclass)
            ORDER BY nspname, proname"""

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
    def create(self, newsrc=None, basetype=False):
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
                         args, self.returns, self.language, volat, leakproof,
                         strict, secdef, cost, rows, config, src))
        return stmts

    def alter(self, infunction, no_owner=False):
        """Generate SQL to transform an existing function

        :param infunction: a YAML map defining the new function
        :return: list of SQL statements

        Compares the function to an input function and generates SQL
        statements to transform it into the one represented by the
        input.
        """
        stmts = []
        if self.source != infunction.source and infunction.source is not None:
            stmts.append(self.create(infunction.source))
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
        from pyrseas.dbobject.dbtype import DbType

        # drop the dependency on the type if this function is an in/out
        # because there is a loop here.
        for dep in list(deps):
            if isinstance(dep, DbType):
                for attr in ('input', 'output', 'send', 'receive'):
                    fname = getattr(dep, attr, None)
                    if fname and fname == self.qualname():
                        deps.remove(dep)
                        self._defining = dep    # we may need a shell for this
                        break

        return deps

    def drop(self):
        # If the function defines a type it will be dropped by the CASCADE
        # on the type.
        if getattr(self, '_defining', None):
            return []
        else:
            return super(Function, self).drop()


class Aggregate(Proc):
    """An aggregate function"""

    def __init__(self, name, schema, description, owner, privileges,
                 arguments, sfunc=None, stype=None, finalfunc=None,
                 initcond=None, sortop=None,
                 oid=None):
        """Initialize the aggregate

        :param name-arguments: see Proc.__init__ params
        :param sfunc: state transition function (from aggtransfn)
        :param stype: state datatype (from aggtranstype)
        :param finalfunc: final function (from aggfinalfn)
        :param initcond: initial value (from agginitval)
        :param sortop: sort operator (from aggsortop)
        """
        super(Aggregate, self).__init__(
            name, schema, description, owner, privileges, arguments)
        self.sfunc = sfunc
        self.stype = stype
        self.finalfunc = finalfunc if finalfunc != '-' else None
        self.initcond = initcond
        self.sortop = sortop if sortop != '0' else None
        self.oid = oid

    @staticmethod
    def query():
        return """
            SELECT nspname AS schema, proname AS name,
                   pg_get_function_identity_arguments(p.oid) AS arguments,
                   rolname AS owner,
                   array_to_string(proacl, ',') AS privileges,
                   aggtransfn::regproc AS sfunc,
                   aggtranstype::regtype AS stype,
                   aggfinalfn::regproc AS finalfunc,
                   agginitval AS initcond, aggsortop::regoper AS sortop,
                   obj_description(p.oid, 'pg_proc') AS description, p.oid
            FROM pg_proc p JOIN pg_roles r ON (r.oid = proowner)
                 JOIN pg_namespace n ON (pronamespace = n.oid)
                 LEFT JOIN pg_aggregate a ON (p.oid = aggfnoid)
            WHERE (nspname != 'pg_catalog' AND nspname != 'information_schema')
              AND proisagg
              AND p.oid NOT IN (
                  SELECT objid FROM pg_depend WHERE deptype = 'e'
                               AND classid = 'pg_proc'::regclass)
            ORDER BY nspname, proname"""

    def to_map(self, db, no_owner, no_privs):
        """Convert an agggregate to a YAML-suitable format

        :param no_owner: exclude aggregate owner information
        :param no_privs: exclude privilege information
        :return: dictionary
        """
        dct = super(Aggregate, self).to_map(db, no_owner, no_privs)
        for attr in ('initcond', 'finalfunc', 'sortop'):
            if getattr(self, attr) is None:
                dct.pop(attr)
        return dct

    @commentable
    @grantable
    @ownable
    def create(self):
        """Return SQL statements to CREATE the aggregate

        :return: SQL statements
        """
        opt_clauses = []
        if self.finalfunc is not None:
            opt_clauses.append("FINALFUNC = %s" % self.finalfunc)
        if self.initcond is not None:
            opt_clauses.append("INITCOND = '%s'" % self.initcond)
        if self.sortop is not None:
            opt_clauses.append("SORTOP = %s" % self.sortop)
        return ["CREATE AGGREGATE %s(%s) (\n    SFUNC = %s,"
                "\n    STYPE = %s%s%s)" % (
                    self.qualname(), self.arguments, self.sfunc, self.stype,
                    opt_clauses and ',\n    ' or '',
                    ',\n    '.join(opt_clauses))]

    def get_implied_deps(self, db):
        # List the previous dependencies
        deps = super(Aggregate, self).get_implied_deps(db)

        sch, fnc = split_schema_obj(self.sfunc)
        args = self.stype + ', ' + self.arguments
        deps.add(db.functions[sch, fnc, args])
        if self.finalfunc is not None:
            sch, fnc = split_schema_obj(self.finalfunc)
            deps.add(db.functions[sch, fnc, self.stype])

        return deps


class ProcDict(DbObjectDict):
    "The collection of regular and aggregate functions in a database"

    cls = Proc

    def _from_catalog(self):
        """Initialize the dictionary of procedures by querying the catalogs"""
        self.cls = Function
        for func in self.fetch():
            self[func.key()] = func
            self.by_oid[func.oid] = func
        self.cls = Aggregate
        for aggr in self.fetch():
            self[aggr.key()] = aggr
            self.by_oid[aggr.oid] = aggr

    def from_map(self, schema, infuncs):
        """Initalize the dictionary of functions by converting the input map

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
                src = inobj.get('source', None)
                obj = inobj.get('obj_file', None)
                if (src and obj) or not (src or obj):
                    raise ValueError("Function '%s': either source or "
                                     "obj_file must be specified" % fnc)
                self[(schema.name, fnc, arguments)] = func = Function(
                    fnc, schema.name, inobj.pop('description', None),
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
            else:
                self[(schema.name, fnc, arguments)] = func = Aggregate(
                    fnc, schema.name, inobj.pop('description', None),
                    inobj.pop('owner', None), inobj.pop('privileges', []),
                    arguments, inobj.pop('sfunc', None),
                    inobj.pop('stype', None), inobj.pop('finalfunc', None),
                    inobj.pop('initcond', None), inobj.pop('sortop', None))
            func.privileges = privileges_from_map(func.privileges,
                                                  func.allprivs, func.owner)

    def find(self, func, args):
        """Return a function given its name and arguments

        :param func: name of the function, eventually with schema
        :param args: list of type names

        Return the function found, else None.
        """
        schema, name = split_schema_obj(func)
        args = ', '.join(args)
        return self.get((schema, name, args))

    def link_refs(self, dbtypes, dbeventtrigs):
        """Connect the functions to other objects

        - Connect event triggers to the functions executed
        - Connect defining functions to the type they define

        :param dbtypes: dictionary of types
        :param dbeventtrigs: dictionary of event triggers

        Fills in the `event_triggers` list for each function by
        traversing the `dbeventtrigs` dictionary.
        """
        for key in dbeventtrigs:
            evttrg = dbeventtrigs[key]
            (sch, fnc) = split_schema_obj(evttrg.procedure)
            func = self[(sch, fnc[:-2], '')]
            if not hasattr(func, 'event_triggers'):
                func.event_triggers = []
            func.event_triggers.append(evttrg.name)

        # TODO: this link is needed from map, not from sql.
        # is this a pattern? I was assuming link_refs would have disappeared
        # but I'm actually still maintaining them. Verify if they are always
        # only used for from_map, not for from_catalog
        for key in dbtypes:
            t = dbtypes[key]
            for f in t.find_defining_funcs(self):
                f._defining = t
