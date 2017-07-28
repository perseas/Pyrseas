#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""dbtoyaml - extract the schema of a PostgreSQL database in YAML format"""

from __future__ import print_function
import sys

from pyrseas import __version__
from pyrseas.yamlutil import yamldump
from pyrseas.database import Database
from pyrseas.cmdargs import cmd_parser, parse_args


def main(schema=None):
    """Convert database table specifications to YAML."""
    parser = cmd_parser("Extract the schema of a PostgreSQL database in "
                        "YAML format", __version__)
    parser.add_argument('-m', '--multiple-files', action='store_true',
                        help='output to multiple files (metadata directory)')
    parser.add_argument('-O', '--no-owner', action='store_true',
                        help='exclude object ownership information')
    parser.add_argument('-x', '--no-privileges', action='store_true',
                        dest='no_privs',
                        help='exclude privilege (GRANT/REVOKE) information')
    group = parser.add_argument_group("Object inclusion/exclusion options",
                                      "(each can be given multiple times)")
    group.add_argument('-n', '--schema', metavar='SCHEMA', dest='schemas',
                       action='append', default=[],
                       help="extract the named schema(s) (default all)")
    group.add_argument('-N', '--exclude-schema', metavar='SCHEMA',
                       dest='excl_schemas', action='append', default=[],
                       help="do NOT extract the named schema(s) "
                       "(default none)")
    group.add_argument('-t', '--table', metavar='TABLE', dest='tables',
                       action='append', default=[],
                       help="extract the named table(s) (default all)")
    group.add_argument('-T', '--exclude-table', metavar='TABLE',
                       dest='excl_tables', action='append', default=[],
                       help="do NOT extract the named table(s) "
                       "(default none)")
    parser.set_defaults(schema=schema)
    cfg = parse_args(parser)
    output = cfg['files']['output']
    options = cfg['options']
    if options.multiple_files and output:
        parser.error("Cannot specify both --multiple-files and --output")

    db = Database(cfg)
    dbmap = db.to_map()

    if not options.multiple_files:
        print(yamldump(dbmap), file=output or sys.stdout)
        if output:
            output.close()

if __name__ == '__main__':
    main()
