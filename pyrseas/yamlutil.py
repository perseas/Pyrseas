# -*- coding: utf-8 -*-
"""Pyrseas YAML utilities"""

from yaml import add_representer, dump

class MultiLineStr(str):
    """ Marker for multiline strings"""


def MultiLineStr_presenter(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
add_representer(MultiLineStr, MultiLineStr_presenter)


def yamldump(objmap):
    """Dump an object map using yaml.dump with certain defaults

    :param objmap: dictionary
    :return: dumped object map
    """
    return dump(objmap, default_flow_style=False, allow_unicode=True)
