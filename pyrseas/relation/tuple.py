# -*- coding: utf-8 -*-
"""
    pyrseas.relation.tuple
"""
from datetime import datetime, time
from pyrseas.relation.attribute import Attribute

RESERVED_ATTRIBUTE_NAMES = (
    '_heading', '_nullable_attribs', '_tuple_version', '_sysdefault_attribs')


class Tuple(object):
    "A relational n-tuple: a set of attributes"

    def __init__(self, attribs):
        """Initialize a relational tuple

        :param attribs: list of Attributes (or single Attribute)
        """
        if not isinstance(attribs, list):
            attribs = [attribs]
        self._sysdefault_attribs = []
        self._nullable_attribs = []
        self._tuple_version = None
        heading = []
        for attr in attribs:
            assert isinstance(attr, Attribute)
            assert attr.name not in RESERVED_ATTRIBUTE_NAMES, \
                "Cannot use '%s' as attribute name" % attr.name
            setattr(self, attr.name, attr.value)
            heading.append((attr.name, attr.type))
            if attr.sysdefault:
                self._sysdefault_attribs.append(attr.name)
            if attr.nullable:
                self._nullable_attribs.append(attr.name)
        # This has to be last for __setattr__
        self._heading = tuple(heading)

    def __setattr__(self, name, value):
        if not hasattr(self, '_heading') or name == '_tuple_version':
            object.__setattr__(self, name, value)
            return
        assert name not in RESERVED_ATTRIBUTE_NAMES, \
            "Attribute '%s' cannot be set" % name
        if not name in self.__dict__:
            raise AttributeError("%r has no attribute '%s'" % (self, name))
        attrdict = dict(self._heading)
        attr = Attribute(name, attrdict[name], value,
                         nullable=name in self._nullable_attribs)
        object.__setattr__(self, name, attr.value)

    def __repr__(self):
        return "Tuple(%s)" % ", ".join("%s %s" % (name, type_.__name__)
                                       for name, type_ in self._heading)


def tuple_values_dict(currtuple, newtuple=None):
    """Return dictionary of attributes with their values

    :param currtuple: current Tuple
    :param newtuple: optional Tuple with new values
    :return: dictionary of attributes and values
    """
    valdict = {}
    for attr in currtuple.__dict__:
        if attr in RESERVED_ATTRIBUTE_NAMES:
            continue
        currval = getattr(currtuple, attr)
        if newtuple is None:
            valdict.update({attr: currval})
        elif hasattr(newtuple, attr):
            newval = getattr(newtuple, attr)
            try:
                diff = currval != newval
            except TypeError:
                # TODO: more needed for naive vs. aware datetime/time
                if isinstance(newval, datetime) or isinstance(newval, time):
                    if newval.utcoffset() is None:
                        diff = True
                else:
                    raise
            if diff:
                valdict.update({attr: newval})
    if newtuple is not None:
        for newattr in newtuple.__dict__:
            if newattr in RESERVED_ATTRIBUTE_NAMES:
                continue
            if newattr not in currtuple.__dict__:
                valdict.update({newattr: getattr(newtuple, newattr)})
    return valdict
