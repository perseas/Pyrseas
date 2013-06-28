# -*- coding: utf-8 -*-
"""Utility module for command line argument parsing"""

from argparse import ArgumentParser, FileType

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


def cmd_parser(description, version, config={}):
    """Create command line argument parser with common PostgreSQL options

    :return: the created parser
    """
    parent = ArgumentParser(add_help=False)
    parent.add_argument('dbname', help='database name')
    group = parent.add_argument_group('Connection options')
    cfg = config['database'] if 'database' in config else {}
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
