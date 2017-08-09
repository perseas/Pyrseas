# -*- coding: utf-8 -*-
"""
    pyrseas.augment.function
    ~~~~~~~~~~~~~~~~~~~~~~~~

    This module defines two classes: CfgFunction derived from
    DbAugment and CfgFunctionDict derived from DbAugmentDict.
"""
from pyrseas.augment import DbAugmentDict, DbAugment
from pyrseas.dbobject.function import Function


class CfgFunctionSource(DbAugment):
    "A configuration function source or part thereof"
    pass


class CfgFunctionTemplate(CfgFunctionSource):
    "A configuration function source template"

    pass


class CfgFunctionSourceDict(DbAugmentDict):

    cls = CfgFunctionSource

    def __init__(self, cfg_templates):
        for templ in cfg_templates:
            src = cfg_templates[templ]
            dct = {'source': src}
            self[templ] = CfgFunctionTemplate(name=templ, **dct)

    def from_map(self, intempls):
        """Initialize the dict of templates by converting the input list

        :param intempls: YAML list defining the function templates
        """
        for templ in intempls:
            self[templ] = CfgFunctionTemplate(
                name=templ, source=intempls[templ])


class CfgFunction(DbAugment):
    "A configuration function definition"

    keylist = ['name', 'arguments']

    def apply(self, schema, trans_tbl, augdb):
        """Add a function to a given schema.

        :param schema: name of the schema in which to create the function
        :param trans_tbl: translation table
        :param augdb: augmenter dictionaries
        """
        newdict = self.__dict__.copy()
        newdict.pop('name')
        newdict.pop('description')
        newfunc = Function(self.name, schema, self.description, None, [],
                           **newdict)
        src = newfunc.source
        if '{{' in src and '}}' in src:
            pref = src.find('{{')
            prefix = src[:pref]
            suf = src.find('}}')
            suffix = src[suf + 2:]
            tmplkey = src[pref + 2:suf]
            if tmplkey not in augdb.funcsrcs:
                if '{{'+tmplkey+'}}' not in [pat for (pat, repl) in trans_tbl]:
                    raise KeyError("Function template '%s' not found" %
                                   tmplkey)
            else:
                newfunc.source = prefix + augdb.funcsrcs[tmplkey].source + \
                    suffix

        for (pat, repl) in trans_tbl:
            if '{{' in newfunc.source:
                newfunc.source = newfunc.source.replace(pat, repl)
            if '{{' in newfunc.name:
                newfunc.name = newfunc.name.replace(pat, repl)
            if '{{' in newfunc.description:
                newfunc.description = newfunc.description.replace(pat, repl)
        return newfunc


class CfgFunctionDict(DbAugmentDict):
    "The collection of configuration functions"

    cls = CfgFunction

    def __init__(self, config):
        for func in config:
            fncdict = config[func]
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
