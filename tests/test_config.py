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
CFG_DATA = {'datacopy': CFG_TABLE_DATA}
CFG_FILE = 'testcfg.yaml'


def test_defaults():
    "Create a configuration with defaults"
    cfg = Config()
    for key in ['audit_columns', 'functions', 'function_templates', 'columns',
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
    ucfg = tmpdir.join(CFG_FILE)
    ucfg.write(yamldump({'repository': {'path': tmpdir.strpath}}))
    f = tmpdir.join("config.yaml")
    f.write(yamldump(CFG_DATA))
    os.environ["PYRSEAS_USER_CONFIG"] = ucfg.strpath
    cfg = Config()
    assert cfg['datacopy'] == CFG_TABLE_DATA


def test_cmd_parser(tmpdir):
    "Test parsing a configuration file specified on the command line"
    f = tmpdir.join(CFG_FILE)
    f.write(yamldump(CFG_DATA))
    sys.argv = ['testprog', '--dbname', 'testdb', '--config', f.strpath]
    os.environ["PYRSEAS_USER_CONFIG"] = ''
    parser = cmd_parser("Test description", '0.0.1')
    cfg = parse_args(parser)
    assert cfg['datacopy'] == CFG_TABLE_DATA


def test_parse_repo_config(tmpdir):
    "Test parsing a repository configuration file in the current directory"
    f = tmpdir.join('config.yaml')
    f.write(yamldump(CFG_DATA))
    os.chdir(tmpdir.strpath)
    sys.argv = ['testprog', '--dbname', 'testdb']
    os.environ["PYRSEAS_USER_CONFIG"] = ''
    parser = cmd_parser("Test description", '0.0.1')
    cfg = parse_args(parser)
    assert cfg['datacopy'] == CFG_TABLE_DATA


def test_repo_user_config(tmpdir):
    "Test a repository path specified in the user config"
    usercfg = {'repository': {'path': tmpdir.strpath}}
    userf = tmpdir.join("usercfg.yaml")
    userf.write(yamldump(usercfg))
    os.environ["PYRSEAS_USER_CONFIG"] = userf.strpath
    repof = tmpdir.join("config.yaml")
    repof.write(yamldump(CFG_DATA))
    cfg = Config()
    assert cfg['datacopy'] == CFG_TABLE_DATA
