# -*- coding: utf-8 -*-
"""
    pyrseas.augment
    ~~~~~~~~~~~~~~~

    This defines two low level classes.  Most Database Augmenter
    classes are derived from either DbAugment or DbAugmentDict.
"""


class DbAugment(object):
    "A database augmentation object"

    keylist = ['name']
    """List of attributes that uniquely identify the object"""

    def __init__(self, **attrs):
        """Initialize the augmentation object from a dictionary of attributes

        :param attrs: the dictionary of attributes
        """
        for key, val in list(attrs.items()):
            setattr(self, key, val)


class DbAugmentDict(dict):
    """A dictionary of database augmentations, all of the same type"""

    cls = DbAugment
    """The class, derived from :class:`DbAugment` that the objects belong to.
    """
