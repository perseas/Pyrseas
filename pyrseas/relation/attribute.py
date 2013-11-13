# -*- coding: utf-8 -*-
"""
    pyrseas.relation.attribute
"""
from pyrseas.lib.pycompat import PY2


class Attribute(object):
    "A relational attribute triple: attribute-type-value"

    def __init__(self, name, type_=str, value=None, nullable=False,
                 sysdefault=False):
        """Initialize an attribute

        :param name: attribute name
        :param type_: type
        :param value: value
        :param nullable: indicates whether attribute accepts NULLs
        :param sysdefault: indicates whether attribute has system default
        """
        self.name = name
        self.type = type_
        if value is not None:
            if (isinstance(value, int) and type_ == float and
                    float(value) == value):
                value = float(value)
            if not isinstance(value, type_):
                if not (PY2 and type_ == str and isinstance(value, unicode)):
                    raise ValueError("Value (%s) of %r is not of type '%s'" %
                                     (value, self, type_.__name__))
        self.value = value
        if not nullable:
            if value is None:
                if type_ == str:
                    self.value = ''
                elif type_ == int:
                    self.value = 0
                elif type_ == float:
                    self.value = 0.0
                elif type_ == bool:
                    self.value = False
                elif not sysdefault:
                    raise ValueError("No value provided for %r" % self)
        else:  # nullable
            if (type_ == int and value == 0) or (
                    type_ == bool and value == False) or (
                    type_ == str and value == '') or (
                    type_ == float and value == 0):
                self.value = None
        self.nullable = nullable
        self.sysdefault = sysdefault

    def __repr__(self):
        return "Attribute(%s %s)" % (self.name, self.type.__name__)
