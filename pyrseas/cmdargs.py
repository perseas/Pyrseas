# -*- coding: utf-8 -*-
"""Utility module for command line argument parsing"""

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
    cfg = _cfg['database'] if 'database' in _cfg else {}
    group.add_argument('-H', '--host', **_help_dflt('host', cfg))
    group.add_argument('-p', '--port', type=int, **_help_dflt('port', cfg))
    group.add_argument('-U', '--username', **_help_dflt('username', cfg))
    group.add_argument('-W', '--password', action="store_true",
                       help="force password prompt")
    parent.add_argument('-c', '--config', type=FileType('r'),
                        help="configuration file path")
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
    if 'database' not in _cfg:
        _cfg['database'] = {}
    for key in ['dbname', 'host', 'port', 'username']:
        _cfg['database'][key] = args[key]
        del args[key]
    _cfg['database']['password'] = (getpass.getpass() if args['password']
                                    else None)
    del args['password']
    if 'files' not in _cfg:
        _cfg['files'] = {}
    for key in ['output', 'config']:
        _cfg['files'][key] = args[key]
        del args[key]
    if 'config' in _cfg['files'] and _cfg['files']['config']:
        _cfg.merge(yaml.safe_load(_cfg['files']['config']))
    _cfg['options'] = arg_opts
    return _cfg
