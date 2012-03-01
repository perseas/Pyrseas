# -*- coding: utf-8 -*-
"""Utility module for command line argument parsing"""

from argparse import ArgumentParser, FileType


def parent_parser():
    """Create command line argument parser with common PostgreSQL options

    :return: the created parser
    """
    parser = ArgumentParser(add_help=False)
    parser.add_argument('dbname', help='database name')
    parser.add_argument('-H', '--host', help="database server host or "
                        "socket directory (default %(default)s)")
    parser.add_argument('-p', '--port', type=int, help="database server port "
                        "number (default %(default)s)")
    parser.add_argument('-U', '--username', dest='user',
                        help="database user name (default %(default)s)")
    parser.add_argument('-W', '--password', action="store_true",
                        help="force password prompt")
    parser.add_argument('-o', '--output', type=FileType('w'),
                        help="output file name (default stdout)")
    parser.add_argument('--version', action='version', version='%(prog)s 0.4')
    return parser
