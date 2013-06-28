#!/usr/bin/python
# -*- coding: utf-8 -*-
"""dbtoyaml - extract the schema of a PostgreSQL database in YAML format"""

from __future__ import print_function
import sys
import getpass

from pyrseas import __version__
from pyrseas.config import Config
from pyrseas.yamlutil import yamldump
from pyrseas.database import Database
from pyrseas.cmdargs import cmd_parser


def main(schema=None):
    """Convert database table specifications to YAML."""
    cfg = Config()
    parser = cmd_parser("Extract the schema of a PostgreSQL database in "
                        "YAML format", __version__, cfg)
    parser.add_argument('-d', '--directory',
                        help='root directory for output')
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
    args = parser.parse_args()
    if args.directory and args.output:
        parser.error("Cannot specify both directory and file output")

    pswd = (args.password and getpass.getpass() or None)
    db = Database(args.dbname, args.username, pswd, args.host, args.port)
    dbmap = db.to_map(args)

    if not args.directory:
        print(yamldump(dbmap), file=args.output or sys.stdout)

    if args.output:
        args.output.close()

if __name__ == '__main__':
    main()
