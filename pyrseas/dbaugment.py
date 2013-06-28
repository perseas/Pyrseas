#!/usr/bin/python
# -*- coding: utf-8 -*-
"""dbaugment - Augment a PostgreSQL database"""

from __future__ import print_function
import sys
import getpass
from argparse import FileType

import yaml

from pyrseas import __version__
from pyrseas.config import Config
from pyrseas.yamlutil import yamldump
from pyrseas.augmentdb import AugmentDatabase
from pyrseas.cmdargs import cmd_parser


def main():
    """Augment database specifications"""
    cfg = Config()
    parser = cmd_parser("Generate a modified schema for a PostgreSQL "
                        "database, in YAML format, augmented with specified "
                        "attributes and procedures", __version__, cfg)
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
    args = parser.parse_args()

    pswd = (args.password and getpass.getpass() or None)
    # need to pass config map from config.yaml
    augdb = AugmentDatabase(args.dbname, args.username, pswd, args.host,
                            args.port, cfg)
    augmap = yaml.safe_load(args.spec)
    outmap = augdb.apply(augmap, args)
    print(yamldump(outmap), file=args.output or sys.stdout)
    if args.output:
        args.output.close()

if __name__ == '__main__':
    main()
