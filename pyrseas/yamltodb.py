#!/usr/bin/python
# -*- coding: utf-8 -*-
"""yamltodb - generate SQL statements to update a PostgreSQL database
to match the schema specified in a YAML file"""

from __future__ import print_function
import os
import sys
from argparse import ArgumentParser, FileType

import yaml

from pyrseas.dbconn import DbConnection
from pyrseas.database import Database
from pyrseas.cmdargs import parent_parser


def main(host='localhost', port=5432):
    """Convert YAML specifications to database DDL."""
    parser = ArgumentParser(parents=[parent_parser()],
                            description="Generate SQL statements to update a "
                            "PostgreSQL database to match the schema specified"
                            " in a YAML file")
    parser.add_argument('spec', nargs='?', type=FileType('r'),
                        default=sys.stdin, help='YAML specification')
    parser.add_argument('-1', '--single-transaction', action='store_true',
                        dest='onetrans', help="wrap commands in BEGIN/COMMIT")
    parser.add_argument('-u', '--update', action='store_true',
                        help="apply changes to database (implies -1)")
    parser.add_argument('-n', '--schema', dest='schlist', action='append',
                        help="only for named schemas (default all)")

    parser.set_defaults(host=host, port=port, username=os.getenv("USER"))
    args = parser.parse_args()

    dbconn = DbConnection(args.dbname, args.username, args.password,
                          args.host, args.port)
    db = Database(dbconn)
    inmap = yaml.load(args.spec)
    if args.schlist:
        kschlist = ['schema ' + sch for sch in args.schlist]
        for sch in inmap.keys():
            if sch not in kschlist:
                del inmap[sch]
    stmts = db.diff_map(inmap, args.schlist)
    if args.output:
        fd = args.output
        sys.stdout = fd
    if stmts:
        if args.onetrans or args.update:
            print("BEGIN;")
        print(";\n".join(stmts) + ';')
        if args.onetrans or args.update:
            print("COMMIT;")
        if args.update:
            dbconn.connect()
            try:
                for stmt in stmts:
                    dbconn.conn.cursor().execute(stmt)
            except:
                dbconn.conn.rollback()
                raise
            else:
                dbconn.conn.commit()
                print("Changes applied", file=sys.stderr)
    if args.output:
        fd.close()

if __name__ == '__main__':
    main()
