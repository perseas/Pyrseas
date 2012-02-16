# -*- coding: utf-8 -*-
"""
    pyrseas.extend
    ~~~~~~~~~~~~~~

    This defines two low level classes.  Most Database Extender
    classes are derived from either DbExtension or DbExtensionDict.
"""


class DbExtension(object):
    "A database extension"

    keylist = ['name']
    """List of attributes that uniquely identify the object"""

    def __init__(self, **attrs):
        """Initialize the extension object from a dictionary of attributes

        :param attrs: the dictionary of attributes

        Non-key attributes without a value are discarded.
        """
        for key, val in attrs.items():
            if val or key in self.keylist:
                setattr(self, key, val)


class DbExtensionDict(dict):
    """A dictionary of database extensions, all of the same type"""

    cls = DbExtension
    """The class, derived from :class:`DbExtension` that the objects belong to.
    """
