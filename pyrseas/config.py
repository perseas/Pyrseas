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


def _load_cfg(envvar, alt_dir):
    cfgpath = ''
    cfg = {}
    cfgdir = os.environ.get(envvar, alt_dir)
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

    def __init__(self):
        self.update(_load_cfg("PYRSEAS_SYS_CONFIG", os.path.abspath(
                    os.path.join(os.path.dirname(__file__), '..', 'config'))))
        cfg = _load_cfg("PYRSEAS_USER_CONFIG",
                        os.path.join(_home_dir(), 'pyrseas'))
        for key, val in list(cfg.items()):
            if key in self:
                self[key].update(val)
            else:
                self[key] = val
        cfg = _load_cfg("PYRSEAS_REPO_DIR", None)
        for key, val in list(cfg.items()):
            if key in self:
                self[key].update(val)
            else:
                self[key] = val
