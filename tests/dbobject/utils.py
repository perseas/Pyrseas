# -*- coding: utf-8 -*-
"""Utility functions and classes for testing Pyrseas"""

import os
from unittest import TestCase

from psycopg2 import connect
from psycopg2.extras import DictConnection
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

from pyrseas.dbconn import DbConnection
from pyrseas.database import Database


def fix_indent(stmt):
    "Fix specifications which are in a new line with indentation"
    return stmt.replace('\n    ', ' ').replace('( ', '(')


def pgconnect(dbname, user=None, host='localhost', port=5432):
    "Connect to a Postgres database using psycopg2"
    return connect("host=%s port=%d dbname=%s user=%s" % (
            host, port, dbname, user or os.getenv("USER")),
                     connection_factory=DictConnection)


def pgexecute(dbconn, query):
    "Execute a query using a cursor"
    curs = dbconn.cursor()
    try:
        curs.execute(query)
    except:
        curs.close()
        dbconn.rollback()
        raise
    return curs


def pgexecute_auto(dbconn, query):
    "Execute a query using a cursor with autocommit enabled"
    isolation_level = dbconn.isolation_level
    dbconn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    curs = pgexecute(dbconn, query)
    dbconn.set_isolation_level(isolation_level)
    return curs

DBNAME = 'pyrseas_testdb'

CREATE_DDL = "CREATE DATABASE %s TEMPLATE = template0"


class PostgresDb(object):
    """A PostgreSQL database connection

    This is separate from the one used by DbConnection, because the
    tests need to create and drop databases and other objects,
    independently.
    """
    def __init__(self, name):
        self.name = name
        self.conn = None

    def connect(self):
        """Connect to the database.  If we're not already connected we
        first connect to 'postgres' and see if the given database exists.
        If it doesn't, we create and then connect to it."""
        if not self.conn:
            conn = pgconnect('postgres')
            curs = pgexecute(conn,
                             "SELECT 1 FROM pg_database WHERE datname = '%s'" %
                             self.name)
            row = curs.fetchone()
            if not row:
                curs.close()
                curs = pgexecute_auto(conn, CREATE_DDL % self.name)
                curs.close()
                conn.close()
            self.conn = pgconnect(self.name)

    def close(self):
        "Close the connection if still open"
        if not self.conn:
            return ValueError
        self.conn.close()

    def create(self):
        "Drop the database if it exists and re-create it"
        conn = pgconnect('postgres')
        curs = pgexecute_auto(conn, "DROP DATABASE IF EXISTS %s" % self.name)
        curs = pgexecute_auto(conn, CREATE_DDL % self.name)
        curs.close()
        conn.close()

    def clear(self):
        "Drop tables and other objects"
        query = \
            """SELECT nspname, relname, relkind FROM pg_class
                      JOIN pg_namespace ON (relnamespace = pg_namespace.oid)
                      JOIN pg_roles ON (nspowner = pg_roles.oid)
               WHERE relkind in ('r', 'S')
                     AND (nspname = 'public' OR rolname <> 'postgres')"""
        curs = pgexecute(self.conn, query)
        objs = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for obj in objs:
            if obj['relkind'] == 'r':
                self.execute("DROP TABLE %s.%s CASCADE" % (obj[0], obj[1]))
            elif obj['relkind'] == 'S':
                self.execute("DROP SEQUENCE %s.%s CASCADE" % (obj[0], obj[1]))
        self.conn.commit()

    def drop(self):
        "Drop the database"
        conn = pgconnect('postgres')
        curs = pgexecute_auto(conn, "DROP DATABASE %s" % self.name)
        curs.close()
        conn.close()

    def execute(self, stmt):
        "Execute a DDL statement"
        #print "execute:", stmt
        curs = pgexecute(self.conn, stmt)
        curs.close()

    def execute_commit(self, stmt):
        "Execute a DDL statement and commit"
        self.execute(stmt)
        self.conn.commit()

    def execute_and_map(self, ddlstmt):
        "Execute a DDL statement, commit, and return a map of the database"
        self.execute(ddlstmt)
        self.conn.commit()
        db = Database(DbConnection(self.name))
        return db.to_map()

    def process_map(self, input_map):
        """Process an input map and return the SQL statements necessary to
        convert the database to match the map."""
        db = Database(DbConnection(self.name))
        stmts = db.diff_map(input_map)
        return stmts


class PyrseasTestCase(TestCase):
    """Base class for most test cases"""

    def setUp(self):
        self.db = PostgresDb(DBNAME)
        self.db.connect()
        self.db.clear()

    def tearDown(self):
        self.db.close()
