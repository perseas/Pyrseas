# -*- coding: utf-8 -*-
"""
    pyrseas.extend.function
    ~~~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: CfgFunction derived from
    DbExtension and CfgFunctionDict derived from DbExtensionDict.
"""
from pyrseas.extend import DbExtensionDict, DbExtension
from pyrseas.dbobject.function import Function


FUNC_AUD_DFLT = """\
BEGIN
    NEW.{{modified_by_user}} = CURRENT_USER;
    NEW.{{modified_timestamp}} = CURRENT_TIMESTAMP;
    RETURN NEW;
END """

CFG_FUNCTIONS = \
    {
    'aud_dflt()': {
            'description':
                "Provides modified_by_user and modified_timestamp " \
                "values for audit columns.",
            'language': 'plpgsql',
            'returns': 'trigger',
            'security_definer': True,
            'source': FUNC_AUD_DFLT}
    }


class CfgFunction(DbExtension):
    "A configuration function definition"

    keylist = ['name', 'arguments']

    def apply(self, schema, col_trans_tbl):
        """Apply a configuration function to a given schema.

        :param schema: name of the schema in which to create the function
        :param col_trans_tbl: column translation table
        """
        newfunc = Function(schema=schema, **self.__dict__)
        newfunc.volatility = 'v'
        for (pat, repl) in col_trans_tbl:
            if not '{{' in newfunc.source:
                break
            newfunc.source = newfunc.source.replace(pat, repl)
        return newfunc


class CfgFunctionDict(DbExtensionDict):
    "The collection of configuration functions"

    cls = CfgFunction

    def __init__(self):
        for func in CFG_FUNCTIONS:
            paren = func.find('(')
            (fnc, args) = (func[:paren], func[paren + 1:-1])
            self[fnc] = CfgFunction(name=fnc, arguments=args,
                                    **CFG_FUNCTIONS[func])

    def from_map(self, infuncs):
        """Initialize the dictionary of functions by converting the input list

        :param infuncs: YAML list defining the functions
        """
        for func in infuncs:
            paren = func.find('(')
            (fnc, args) = (func[:paren], func[paren + 1:-1])
            if fnc in self:
                cfnc = self[fnc]
            else:
                self[fnc] = cfnc = CfgFunction(name=fnc, arguments=args)
            for attr, val in infuncs[func].items():
                setattr(cfnc, attr, val)
