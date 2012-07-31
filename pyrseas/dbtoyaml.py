#!/usr/bin/python
# -*- coding: utf-8 -*-
"""dbtoyaml - extract the schema of a PostgreSQL database in YAML format"""

from __future__ import print_function
import os
import sys
import getpass
from argparse import ArgumentParser

import yaml

from pyrseas.database import Database
from pyrseas.cmdargs import parent_parser


def main(host='localhost', port=5432, schema=None):
    """Convert database table specifications to YAML."""
    parser = ArgumentParser(parents=[parent_parser()],
                            description="Extract the schema of a PostgreSQL "
                            "database in YAML format")
    parser.add_argument('-O', '--no-owner', action='store_true',
                        help='exclude object ownership information')
    parser.add_argument('-x', '--no-privileges', action='store_true',
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

    parser.set_defaults(host=host, port=port, schema=schema,
                        username=os.getenv("PGUSER") or os.getenv("USER"))
    args = parser.parse_args()

    pswd = (args.password and getpass.getpass() or None)
    db = Database(args.dbname, args.username, pswd, args.host, args.port)
    dbmap = db.to_map(schemas=args.schemas, tables=args.tables,
                      exclude_schemas=args.excl_schemas,
                      exclude_tables=args.excl_tables,
                      no_owner=args.no_owner, no_privs=args.no_privileges)

    print(yaml.dump(dbmap, default_flow_style=False),
          file=args.output or sys.stdout)

    if args.output:
        args.output.close()

if __name__ == '__main__':
    main()
