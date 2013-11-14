# -*- coding: utf-8 -*-
"""Utility module for command line argument parsing"""

import os
from argparse import ArgumentParser, FileType
import getpass

import yaml

from pyrseas.config import Config

_cfg = None

HELP_TEXT = {
    'host': "database server host or socket directory",
    'port': "database server port number",
    'username': "database user name"
}


def _help_dflt(arg, config):
    kwdargs = {'help': HELP_TEXT[arg]}
    if arg in config:
        kwdargs['help'] += " (default %(default)s)"
        kwdargs['default'] = config[arg]
    return kwdargs


def _repo_path(cfg, key=None):
    """Return path to root directory of repository or subdirectory

    :return: path
    """
    repo = cfg['repository']
    if 'path' in repo:
        path = repo['path']
    else:
        path = os.getcwd()
    subdir = '' if key is None else repo[key]
    return os.path.normpath(os.path.join(path, subdir))


def cmd_parser(description, version):
    """Create command line argument parser with common PostgreSQL options

    :param description: text to display before the argument help
    :param version: version of the caller
    :return: the created parser
    """
    global _cfg

    parent = ArgumentParser(add_help=False)
    parent.add_argument('dbname', help='database name')
    group = parent.add_argument_group('Connection options')
    if _cfg is None:
        _cfg = Config()
    dbcfg = _cfg['database'] if 'database' in _cfg else {}
    group.add_argument('-H', '--host', **_help_dflt('host', dbcfg))
    group.add_argument('-p', '--port', type=int, **_help_dflt('port', dbcfg))
    group.add_argument('-U', '--username', **_help_dflt('username', dbcfg))
    group.add_argument('-W', '--password', action="store_true",
                       help="force password prompt")
    parent.add_argument('-c', '--config', type=FileType('r'),
                        help="configuration file path")
    parent.add_argument('-r', '--repository', default=_repo_path(_cfg),
                        help="root of repository (default %(default)s)")
    parent.add_argument('-o', '--output', type=FileType('w'),
                        help="output file name (default stdout)")
    parser = ArgumentParser(parents=[parent], description=description)
    parser.add_argument('--version', action='version',
                        version='%(prog)s ' + '%s' % version)
    return parser


def parse_args(parser):
    """Parse command line arguments and return configuration object

    :param parser: ArgumentParser created by cmd_parser
    :return: a Configuration object
    """
    arg_opts = parser.parse_args()
    args = vars(arg_opts)
    for key in ['database', 'files']:
        if key not in _cfg:
            _cfg[key] = {}

    def tfr(prim, key, val):
        _cfg[prim][key] = val
        del args[key]

    for key in ['dbname', 'host', 'port', 'username']:
        tfr('database', key, args[key])
    tfr('database', 'password',
        (getpass.getpass() if args['password'] else None))

    for key in ['output', 'config']:
        tfr('files', key, args[key])

    if 'config' in _cfg['files'] and _cfg['files']['config']:
        _cfg.merge(yaml.safe_load(_cfg['files']['config']))
    if 'repository' in args:
        if args['repository'] != os.getcwd():
            _cfg['repository']['path'] = args['repository']
        del args['repository']

    _cfg['files']['metadata_path'] = _repo_path(_cfg, 'metadata')
    _cfg['files']['data_path'] = _repo_path(_cfg, 'data')

    _cfg['options'] = arg_opts
    return _cfg
