#!/usr/bin/python
# -*- coding: utf-8 -*-
"""dbaugment - Augment a PostgreSQL database"""

from __future__ import print_function
import os
import sys
import getpass
from argparse import ArgumentParser, FileType

import yaml

from pyrseas.yamlutil import yamldump
from pyrseas.augmentdb import AugmentDatabase
from pyrseas.cmdargs import parent_parser


def main(host='localhost', port=5432):
    """Augment database specifications"""
    parser = ArgumentParser(parents=[parent_parser()],
                            description="Augment a PostgreSQL database with "
                            "standard attributes and procedures")
    parser.add_argument('spec', nargs='?', type=FileType('r'),
                        default=sys.stdin, help='YAML augmenter specification')
    parser.add_argument('--merge-spec', dest='mergefile',
                        help="output a merged specification file")
    parser.add_argument('--merge-config', action="store_true",
                        help="include configuration in merged file")

    parser.set_defaults(host=host, port=port,
                        username=os.getenv("PGUSER") or os.getenv("USER"))
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
