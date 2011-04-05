#!/usr/bin/python
# -*- coding: utf-8 -*-
"""dbtoyaml - extract the schema of a PostgreSQL database in YAML format"""

import os
from optparse import OptionParser

import yaml

from pyrseas.dbconn import DbConnection
from pyrseas.database import Database


def main(host='localhost', port=5432, schema=None):
    """Convert database table specifications to YAML."""
    parser = OptionParser("usage: %prog [options] dbname")
    parser.add_option('-H', '--host', dest='host',
                      help="database server host or socket directory "
                      "(default %default)")
    parser.add_option('-p', '--port', dest='port', type='int',
                     help="database server port (default %default)")
    parser.add_option('-U', '--username', dest='username',
                     help="database user name (default %default)")
    parser.add_option('-n', '--schema', dest='schema',
                     help="only for named schema (default %default)")
    parser.add_option('-t', '--table', dest='tablist', action='append',
                     help="only for named tables (default all)")

    parser.set_defaults(host=host, port=port, username=os.getenv("USER"),
                        schema=schema)
    (options, args) = parser.parse_args()
    if len(args) > 1:
        parser.error("too many arguments")
    elif len(args) != 1:
        parser.error("database name not specified")
    dbname = args[0]

    db = Database(DbConnection(dbname, options.username, options.host,
                               options.port))
    dbmap = db.to_map()
    # trim the map of schemas/tables not selected
    if options.schema:
        skey = 'schema ' + options.schema
        for sch in dbmap.keys():
            if sch != skey:
                del dbmap[sch]
    if options.tablist:
        ktablist = ['table ' + tbl for tbl in options.tablist]
        for sch in dbmap.keys():
            for tbl in dbmap[sch].keys():
                if tbl not in ktablist:
                    del dbmap[sch][tbl]
            if not dbmap[sch]:
                del dbmap[sch]

    print yaml.dump(dbmap, default_flow_style=False)

if __name__ == '__main__':
    main()
