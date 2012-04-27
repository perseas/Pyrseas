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

FUNC_COPY_DENORM = """\
BEGIN
    IF TG_OP = 'INSERT' THEN
        SELECT {{parent_column}}
               INTO NEW.{{child_column}}
        FROM {{parent_schema}}.{{parent_table}}
        WHERE {{parent_key}} = NEW.{{child_fkey}};
    ELSIF TG_OP = 'UPDATE' AND (
           NEW.{{child_fkey}} IS DISTINCT FROM OLD.{{child_fkey}} OR
           NEW.{{child_column}} IS NULL) THEN
        SELECT {{parent_column}}
               INTO NEW.{{child_column}}
        FROM {{parent_schema}}.{{parent_table}}
        WHERE {{parent_key}} = NEW.{{child_fkey}};
    ELSE
        NEW.{{child_column}} := OLD.{{child_column}};
    END IF;
    RETURN NEW;
END """

FUNC_COPY_CASCADE = """\
BEGIN
    IF TG_OP = 'UPDATE' AND (
            NEW.{{parent_column}} IS DISTINCT FROM OLD.{{parent_column}}) THEN
        UPDATE {{child_schema}}.{{child_table}}
        SET {{child_column}} = NULL
        WHERE {{child_fkey}} = NEW.{{child_fkey}};
    END IF;
    RETURN NULL;
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
            'source': FUNC_AUD_DFLT},
    'copy_denorm()': {
            'description':
                "Copies into column {{child_table}}.{{child_column}} " \
                "from {{parent_table}}.{{parent_column}}.",
            'language': 'plpgsql',
            'name': '{{child_table}}_denorm',
            'returns': 'trigger',
            'source': FUNC_COPY_DENORM},
    'copy_cascade()': {
            'description':
                "Forces cascade of {{parent_table}}.{{parent_column}} " \
                "onto {{child_table}}.{{child_column}}.",
            'language': 'plpgsql',
            'name': '{{parent_table}}_cascade',
            'returns': 'trigger',
            'source': FUNC_COPY_CASCADE}
    }


class CfgFunction(DbExtension):
    "A configuration function definition"

    keylist = ['name', 'arguments']

    def adjust_name(self, trans_tbl):
        """Replace function configuration name by actual name

        :param trans_tbl: translation table
        """
        name = self.name
        if '{{' in name:
            for (pat, repl) in trans_tbl:
                if pat in name:
                    name = name.replace(pat, repl)
                    break
        return name

    def apply(self, schema, trans_tbl):
        """Apply a configuration function to a given schema.

        :param schema: name of the schema in which to create the function
        :param trans_tbl: translation table
        """
        newfunc = Function(schema=schema, **self.__dict__)
        newfunc.volatility = 'v'
        for (pat, repl) in trans_tbl:
            if '{{' in newfunc.source:
                newfunc.source = newfunc.source.replace(pat, repl)
            if '{{' in newfunc.name:
                newfunc.name = newfunc.name.replace(pat, repl)
            if '{{' in newfunc.description:
                newfunc.description = newfunc.description.replace(pat, repl)
        return newfunc


class CfgFunctionDict(DbExtensionDict):
    "The collection of configuration functions"

    cls = CfgFunction

    def __init__(self):
        for func in CFG_FUNCTIONS:
            fncdict = CFG_FUNCTIONS[func]
            paren = func.find('(')
            (fnc, args) = (func[:paren], func[paren + 1:-1])
            fncname = fnc
            dct = fncdict.copy()
            if 'name' in dct:
                fncname = dct['name']
                del dct['name']
            self[fnc] = CfgFunction(name=fncname, arguments=args, **dct)

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
            for attr, val in list(infuncs[func].items()):
                setattr(cfnc, attr, val)
