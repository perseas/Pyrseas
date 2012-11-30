"""Pyrseas YAML utilities"""

from yaml import add_representer


class MultiLineStr(str):
    """ Marker for multiline strings"""


def MultiLineStr_presenter(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')
add_representer(MultiLineStr, MultiLineStr_presenter)
