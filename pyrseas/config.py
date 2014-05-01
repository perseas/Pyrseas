# -*- coding: utf-8 -*-
"""Utility module for configuration file parsing"""

import os
import sys

import yaml


CFG_FILE = os.environ.get("PYRSEAS_CONFIG_FILE", "config.yaml")


def _home_dir():
    if sys.platform == 'win32':
        dir = os.getenv('APPDATA', '')
    else:
        dir = os.path.join(os.environ['HOME'], '.config')
    return os.path.abspath(dir)


def _load_cfg(cfgdir):
    cfgpath = ''
    cfg = {}
    if cfgdir is not None:
        if os.path.isdir(cfgdir):
            cfgpath = os.path.join(cfgdir, CFG_FILE)
        elif os.path.isfile(cfgdir):
            cfgpath = cfgdir
        if os.path.exists(cfgpath):
            with open(cfgpath) as f:
                cfg = yaml.safe_load(f)
    return cfg


class Config(dict):
    "A configuration dictionary"

    def __init__(self, sys_only=False):
        self.update(_load_cfg(
            os.environ.get("PYRSEAS_SYS_CONFIG", os.path.abspath(os.path.join(
                           os.path.dirname(__file__))))))
        if sys_only:
            return
        self.merge(_load_cfg(os.environ.get("PYRSEAS_USER_CONFIG",
                             os.path.join(_home_dir(), 'pyrseas'))))
        if 'repository' in self and 'path' in self['repository']:
            cfgpath = self['repository']['path']
        else:
            cfgpath = os.getcwd()
        self.merge(_load_cfg(cfgpath))

    def merge(self, cfg):
        """Merge extra configuration

        :param cfg: extra configuration (dict)
        """
        for key, val in list(cfg.items()):
            if key in self:
                self[key].update(val)
            else:
                self[key] = val
