#!/usr/bin/python
# -*- coding: utf-8 -*-
"""dbextend - Extend a PostgreSQL database"""

from __future__ import print_function
import os
import sys
from optparse import OptionParser

import yaml

from pyrseas.dbconn import DbConnection
from pyrseas.extenddb import ExtendDatabase


def main(host='localhost', port=5432):
    """Convert database table specifications to YAML."""
    parser = OptionParser("usage: %prog [options] dbname spec")
    parser.add_option('-H', '--host', dest='host',
                      help="database server host or socket directory "
                      "(default %default)")
    parser.add_option('-p', '--port', dest='port', type='int',
                     help="database server port (default %default)")
    parser.add_option('-U', '--username', dest='username',
                     help="database user name (default %default)")
    parser.add_option('-W', '--password', action="store_true",
                     help="force password prompt")
    parser.add_option('-o', '--output', dest='filename',
                      help="output file name (default stdout)")
    parser.add_option('--merge-spec', dest='mergefile',
                      help="output a merged specification file")
    parser.add_option('--merge-config', action="store_true",
                      help="include configuration in merged file")

    parser.set_defaults(host=host, port=port, username=os.getenv("USER"))
    (options, args) = parser.parse_args()
    if len(args) > 2:
        parser.error("too many arguments")
    elif len(args) != 2:
        parser.error("missing arguments")
    dbname = args[0]
    extspec = args[1]

    extdb = ExtendDatabase(DbConnection(dbname, options.username,
                                     options.password, options.host,
                                     options.port))
    extmap = yaml.load(open(extspec))
    outmap = extdb.apply(extmap)
    if options.filename:
        fd = open(options.filename, 'w')
        sys.stdout = fd
    print(yaml.dump(outmap, default_flow_style=False))
    if options.filename:
        fd.close()

if __name__ == '__main__':
    main()
