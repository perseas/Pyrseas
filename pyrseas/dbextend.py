#!/usr/bin/python
# -*- coding: utf-8 -*-
"""dbextend - Extend a PostgreSQL database"""

from __future__ import print_function
import os
import sys
import getpass
from argparse import ArgumentParser, FileType

import yaml

from pyrseas.extenddb import ExtendDatabase
from pyrseas.cmdargs import parent_parser


def main(host='localhost', port=5432):
    """Convert database table specifications to YAML."""
    parser = ArgumentParser(parents=[parent_parser()],
                            description="Augment a PostgreSQL database with "
                            "standard extensions")
    parser.add_argument('extspec', type=FileType('r'),
                        help='YAML extension specification')
    parser.add_argument('--merge-spec', dest='mergefile',
                        help="output a merged specification file")
    parser.add_argument('--merge-config', action="store_true",
                        help="include configuration in merged file")

    parser.set_defaults(host=host, port=port, username=os.getenv("USER"))
    args = parser.parse_args()

    pswd = (args.password and getpass.getpass() or '')
    extdb = ExtendDatabase(args.dbname, args.username, pswd, args.host,
                           args.port)
    extmap = yaml.load(args.extspec)
    outmap = extdb.apply(extmap)
    if args.output:
        fd = args.output
        sys.stdout = fd
    print(yaml.dump(outmap, default_flow_style=False))
    if args.output:
        fd.close()

if __name__ == '__main__':
    main()
