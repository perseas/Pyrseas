#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""dbaugment - Augment a PostgreSQL database"""

from __future__ import print_function
import sys
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
    # TODO: processing of multiple files, owner and privileges
    parser.add_argument('-m', '--multiple-files', action='store_true',
                        help='multiple files (metadata directory)')
    parser.add_argument('-O', '--no-owner', action='store_true',
                        help='exclude object ownership information')
    parser.add_argument('-x', '--no-privileges', action='store_true',
                        dest='no_privs',
                        help='exclude privilege (GRANT/REVOKE) information')
    parser.add_argument('spec', nargs='?', type=FileType('r'),
                        default=sys.stdin, help='YAML augmenter specification')
    cfg = parse_args(parser)
    output = cfg['files']['output']
    options = cfg['options']
    augdb = AugmentDatabase(cfg)
    augmap = yaml.safe_load(options.spec)
    try:
        outmap = augdb.apply(augmap)
    except BaseException as exc:
        if type(exc) != KeyError:
            raise
        sys.exit("ERROR: %s" % str(exc))
    print(yamldump(outmap), file=output or sys.stdout)
    if output:
        output.close()

if __name__ == '__main__':
    main()
