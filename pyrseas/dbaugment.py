#!/usr/bin/python
# -*- coding: utf-8 -*-
"""dbaugment - Augment a PostgreSQL database"""

from __future__ import print_function
import sys
import getpass
from argparse import FileType

import yaml

from pyrseas import __version__
from pyrseas.yamlutil import yamldump
from pyrseas.augmentdb import AugmentDatabase
from pyrseas.cmdargs import cmd_parser, parse_args


def main():
    """Augment database specifications"""
    parser = cmd_parser("Generate a modified schema for a PostgreSQL "
                        "database, in YAML format, augmented with specified "
                        "attributes and procedures", __version__)
    # TODO: processing of directory, owner and privileges
    parser.add_argument('-d', '--directory',
                        help='root directory for output')
    parser.add_argument('-O', '--no-owner', action='store_true',
                        help='exclude object ownership information')
    parser.add_argument('-x', '--no-privileges', action='store_true',
                        dest='no_privs',
                        help='exclude privilege (GRANT/REVOKE) information')
    parser.add_argument('spec', nargs='?', type=FileType('r'),
                        default=sys.stdin, help='YAML augmenter specification')
    parser.add_argument('--merge-spec', dest='mergefile',
                        help="output a merged specification file")
    parser.add_argument('--merge-config', action="store_true",
                        help="include configuration in merged file")
    cfg = parse_args(parser)
    output = cfg['files']['output']
    options = cfg['options']
    augdb = AugmentDatabase(cfg)
    augmap = yaml.safe_load(options.spec)
    outmap = augdb.apply(augmap)
    print(yamldump(outmap), file=output or sys.stdout)
    if output:
        output.close()

if __name__ == '__main__':
    main()
