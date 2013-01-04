#!/usr/bin/python
# -*- coding: utf-8 -*-
"""yamltodb - generate SQL statements to update a PostgreSQL database
to match the schema specified in a YAML file"""

from __future__ import print_function
import os
import sys
import getpass
from argparse import ArgumentParser, FileType

import yaml

from pyrseas.database import Database
from pyrseas.cmdargs import parent_parser


def main(host='localhost', port=5432):
    """Convert YAML specifications to database DDL."""
    parser = ArgumentParser(parents=[parent_parser()],
                            description="Generate SQL statements to update a "
                            "PostgreSQL database to match the schema specified"
                            " in a YAML-formatted file(s)")
    parser.add_argument('-d', '--directory',
                        help='root directory for input YAML files')
    parser.add_argument('spec', nargs='?', type=FileType('r'),
                        default=sys.stdin, help='YAML specification')
    parser.add_argument('-1', '--single-transaction', action='store_true',
                        dest='onetrans', help="wrap commands in BEGIN/COMMIT")
    parser.add_argument('-u', '--update', action='store_true',
                        help="apply changes to database (implies -1)")
    parser.add_argument('-n', '--schema', metavar='SCHEMA', dest='schemas',
                        action='append', default=[],
                        help="process only named schema(s) (default all)")

    parser.set_defaults(host=host, port=port,
                        username=os.getenv("PGUSER") or os.getenv("USER"))
    args = parser.parse_args()

    pswd = (args.password and getpass.getpass() or None)
    db = Database(args.dbname, args.username, pswd, args.host, args.port)
    if args.directory:
        inmap = db.map_from_dir(args.directory)
    else:
        inmap = yaml.load(args.spec)

    stmts = db.diff_map(inmap, args.schemas)
    if stmts:
        fd = args.output or sys.stdout
        if args.onetrans or args.update:
            print("BEGIN;", file=fd)
        print(";\n".join(stmts) + ';', file=fd)
        if args.onetrans or args.update:
            print("COMMIT;", file=fd)
        if args.update:
            try:
                for stmt in stmts:
                    db.dbconn.execute(stmt)
            except:
                db.dbconn.rollback()
                raise
            else:
                db.dbconn.commit()
                print("Changes applied", file=sys.stderr)
        if args.output:
            args.output.close()

if __name__ == '__main__':
    main()
