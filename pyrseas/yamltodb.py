#!/usr/bin/python
# -*- coding: utf-8 -*-
"""yamltodb - generate SQL statements to update a PostgreSQL database
to match the schema specified in a YAML file"""

import os
from optparse import OptionParser

import yaml

from pyrseas.dbconn import DbConnection
from pyrseas.database import Database


def main(host='localhost', port=5432):
    """Convert YAML specifications to database DDL."""
    parser = OptionParser("usage: %prog [options] dbname yamlspec")
    parser.add_option('-H', '--host', dest='host',
                      help="database server host or socket directory "
                      "(default %default)")
    parser.add_option('-p', '--port', dest='port', type='int',
                     help="database server port (default %default)")
    parser.add_option('-U', '--username', dest='username',
                     help="database user name (default %default)")
    parser.add_option('-1', '--single-transaction', action='store_true',
                      dest='onetrans',
                      help="wrap commands in BEGIN/COMMIT")
    parser.add_option('-n', '--schema', dest='schlist', action='append',
                     help="only for named schemas (default all)")

    parser.set_defaults(host=host, port=port, username=os.getenv("USER"))
    (options, args) = parser.parse_args()
    if len(args) > 2:
        parser.error("too many arguments")
    elif len(args) != 2:
        parser.error("missing arguments")
    dbname = args[0]
    yamlspec = args[1]

    db = Database(DbConnection(dbname, options.username, options.host,
                               options.port))
    inmap = yaml.load(open(yamlspec))
    if options.schlist:
        kschlist = ['schema ' + sch for sch in options.schlist]
        for sch in inmap.keys():
            if sch not in kschlist:
                del inmap[sch]
    stmts = db.diff_map(inmap, options.schlist)
    if stmts:
        if options.onetrans:
            print "BEGIN;"
        print ";\n".join(stmts) + ';'
        if options.onetrans:
            print "COMMIT;"

if __name__ == '__main__':
    main()
