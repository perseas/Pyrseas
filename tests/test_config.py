# -*- coding: utf-8 -*-
"""Test configuration files"""

import os
import sys

from pyrseas.config import Config
from pyrseas.cmdargs import cmd_parser, parse_args
from pyrseas.yamlutil import yamldump

USER_CFG_DATA = {'database': {'port': 5433},
                 'output': {'version_comment': True}}
CFG_TABLE_DATA = {'schema public': ['t1', 't2']}
CFG_DATA = {'dataload': CFG_TABLE_DATA}
CFG_FILE = 'testcfg.yaml'


def test_defaults():
    "Create a configuration with defaults"
    cfg = Config()
    for key in ['audit_columns', 'functions', 'func_templates', 'columns',
                'triggers']:
        assert key in cfg['augmenter']
    for key in ['metadata', 'data']:
        assert key in cfg['repository']


def test_user_config(tmpdir):
    "Test a user configuration file"
    f = tmpdir.join(CFG_FILE)
    f.write(yamldump(USER_CFG_DATA))
    os.environ["PYRSEAS_USER_CONFIG"] = f.strpath
    cfg = Config()
    assert cfg['database'] == {'port': 5433}
    assert cfg['output'] == {'version_comment': True}


def test_repo_config(tmpdir):
    "Test a repository configuration file"
    f = tmpdir.join("config.yaml")
    f.write(yamldump(CFG_DATA))
    os.environ["PYRSEAS_REPO_DIR"] = tmpdir.strpath
    cfg = Config()
    assert cfg['dataload'] == CFG_TABLE_DATA


def test_cmd_parser(tmpdir):
    "Test parsing a configuration file specified on the command line"
    f = tmpdir.join(CFG_FILE)
    f.write(yamldump(CFG_DATA))
    sys.argv = ['testprog', 'testdb', '--config', f.strpath]
    os.environ["PYRSEAS_USER_CONFIG"] = ''
    os.environ["PYRSEAS_REPO_DIR"] = ''
    parser = cmd_parser("Test description", '0.0.1')
    cfg = parse_args(parser)
    assert cfg['dataload'] == CFG_TABLE_DATA


def test_repo_user_config(tmpdir):
    "Test a repository path specified in the user config"
    usercfg = {'repository': {'path': tmpdir.strpath}}
    userf = tmpdir.join("usercfg.yaml")
    userf.write(yamldump(usercfg))
    os.environ["PYRSEAS_USER_CONFIG"] = userf.strpath
    repof = tmpdir.join("config.yaml")
    repof.write(yamldump(CFG_DATA))
    cfg = Config()
    assert cfg['dataload'] == CFG_TABLE_DATA
