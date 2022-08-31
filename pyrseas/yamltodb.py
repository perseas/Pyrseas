#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""yamltodb - generate SQL statements to update a PostgreSQL database
to match the schema specified in a YAML file"""

from __future__ import print_function
import sys
from argparse import FileType

import yaml

from pyrseas import __version__
from pyrseas.database import Database
from pyrseas.cmdargs import cmd_parser, parse_args


def main():
    """Convert YAML specifications to database DDL."""
    parser = cmd_parser("Generate SQL statements to update a PostgreSQL "
                        "database to match the schema specified in a "
                        "YAML-formatted file(s)", __version__)
    parser.add_argument('-m', '--multiple-files', action='store_true',
                        help='input from multiple files (metadata directory)')
    parser.add_argument('spec', nargs='?', type=FileType('r'),
                        default=sys.stdin, help='YAML specification')
    parser.add_argument('-1', '--single-transaction', action='store_true',
                        dest='onetrans', help="wrap commands in BEGIN/COMMIT")
    parser.add_argument('-u', '--update', action='store_true',
                        help="apply changes to database (implies -1)")
    parser.add_argument('--revert', action='store_true',
                        help="generate SQL to revert changes (experimental)")
    parser.add_argument('-n', '--schema', metavar='SCHEMA', dest='schemas',
                        action='append', default=[],
                        help="process only named schema(s) (default all)")
    cfg = parse_args(parser)
    output = cfg['files']['output']
    options = cfg['options']
    db = Database(cfg)
    if options.multiple_files:
        inmap = db.map_from_dir()
    else:
        try:
            inmap = yaml.safe_load(options.spec)
        except Exception as exc:
            print("Unable to process the input YAML file")
            print("Error is '%s'" % exc)
            return 1

    stmts = db.diff_map(inmap)
    if stmts:
        fd = output or sys.stdout
        if options.onetrans or options.update:
            print("BEGIN;", file=fd)
        for stmt in stmts:
            if isinstance(stmt, tuple):
                outstmt = "".join(stmt) + '\n'
            else:
                outstmt = "%s;\n" % stmt
            print(outstmt, file=fd)
        if options.onetrans or options.update:
            print("COMMIT;", file=fd)
        if options.update:
            try:
                for stmt in stmts:
                    if isinstance(stmt, tuple):
                        # expected format: (\copy, table, from, path, csv)
                        db.dbconn.copy_from(stmt[3], stmt[1])
                    else:
                        db.dbconn.execute(stmt)
            except:
                db.dbconn.rollback()
                raise
            else:
                db.dbconn.commit()
                print("Changes applied", file=sys.stderr)
        if output:
            output.close()

if __name__ == '__main__':
    main()
