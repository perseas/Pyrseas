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
from pyrseas.cmdargs import cmd_parser


def main():
    """Augment database specifications"""
    parser = cmd_parser("Generate a modified schema for a PostgreSQL "
                        "database, in YAML format, augmented with specified "
                        "attributes and procedures", __version__)
    parser.add_argument('spec', nargs='?', type=FileType('r'),
                        default=sys.stdin, help='YAML augmenter specification')
    parser.add_argument('--merge-spec', dest='mergefile',
                        help="output a merged specification file")
    parser.add_argument('--merge-config', action="store_true",
                        help="include configuration in merged file")
    args = parser.parse_args()

    pswd = (args.password and getpass.getpass() or None)
    augdb = AugmentDatabase(args.dbname, args.username, pswd, args.host,
                            args.port)
    augmap = yaml.safe_load(args.spec)
    outmap = augdb.apply(augmap)
    print(yamldump(outmap), file=args.output or sys.stdout)
    if args.output:
        args.output.close()

if __name__ == '__main__':
    main()
