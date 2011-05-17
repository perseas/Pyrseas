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
    return stmt.replace('   ', ' ').replace('  ', ' ').replace('\n ', ' '). \
        replace('( ', '(')


def new_std_map():
    "Return a standard public schema map with its description"
    return {'schema public': {'description': 'standard public schema'}}


def pgconnect(dbname, user, host, port):
    "Connect to a Postgres database using psycopg2"
    return connect("host=%s port=%d dbname=%s user=%s" % (
            host, port, dbname, user), connection_factory=DictConnection)


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


TEST_DBNAME = os.environ.get("PYRSEAS_TEST_DB", 'pyrseas_testdb')
TEST_USER = os.environ.get("PYRSEAS_TEST_USER", os.getenv("USER"))
TEST_HOST = os.environ.get("PYRSEAS_TEST_HOST", 'localhost')
TEST_PORT = os.environ.get("PYRSEAS_TEST_PORT", 5432)
ADMIN_DB = os.environ.get("PYRSEAS_ADMIN_DB", 'postgres')
CREATE_DDL = "CREATE DATABASE %s TEMPLATE = template0"


class PostgresDb(object):
    """A PostgreSQL database connection

    This is separate from the one used by DbConnection, because the
    tests need to create and drop databases and other objects,
    independently.
    """
    def __init__(self, name, user, host, port):
        self.name = name
        self.conn = None
        self.user = user
        self.host = host
        self.port = int(port)
        self._version = 0

    def connect(self):
        """Connect to the database

        If we're not already connected we first connect to the admin
        database and see if the given database exists.  If it doesn't,
        we create and then connect to it.
        """
        if not self.conn:
            conn = pgconnect(ADMIN_DB, self.user, self.host, self.port)
            curs = pgexecute(conn,
                             "SELECT 1 FROM pg_database WHERE datname = '%s'" %
                             self.name)
            row = curs.fetchone()
            if not row:
                curs.close()
                curs = pgexecute_auto(conn, CREATE_DDL % self.name)
                curs.close()
            conn.close()
            self.conn = pgconnect(self.name, self.user, self.host, self.port)
            curs = pgexecute(self.conn, "SHOW server_version_num")
            self._version = int(curs.fetchone()[0])

    def close(self):
        "Close the connection if still open"
        if not self.conn:
            return ValueError
        self.conn.close()

    @property
    def version(self):
        return self._version

    def create(self):
        "Drop the database if it exists and re-create it"
        conn = pgconnect(ADMIN_DB, self.user, self.host, self.port)
        curs = pgexecute_auto(conn, "DROP DATABASE IF EXISTS %s" % self.name)
        curs = pgexecute_auto(conn, CREATE_DDL % self.name)
        curs.close()
        conn.close()

    def clear(self):
        "Drop tables and other objects"
        curs = pgexecute(
            self.conn,
            """SELECT nspname, relname, relkind FROM pg_class
                      JOIN pg_namespace ON (relnamespace = pg_namespace.oid)
                      JOIN pg_roles ON (nspowner = pg_roles.oid)
               WHERE relkind in ('r', 'S', 'v')
                     AND (nspname = 'public' OR rolname <> 'postgres')
               ORDER BY relkind DESC""")
        objs = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for obj in objs:
            if obj['relkind'] == 'r':
                self.execute("DROP TABLE IF EXISTS %s.%s CASCADE" % (
                        obj[0], obj[1]))
            elif obj['relkind'] == 'S':
                self.execute("DROP SEQUENCE %s.%s CASCADE" % (obj[0], obj[1]))
            elif obj['relkind'] == 'v':
                self.execute("DROP VIEW %s.%s CASCADE" % (obj[0], obj[1]))
        self.conn.commit()
        curs = pgexecute(
            self.conn,
            """SELECT nspname, proname, pg_get_function_arguments(p.oid) AS
                      args
               FROM pg_proc p JOIN pg_namespace n ON (pronamespace = n.oid)
               WHERE (nspname != 'pg_catalog'
                     AND nspname != 'information_schema')""")
        funcs = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for func in funcs:
            self.execute("DROP FUNCTION IF EXISTS %s.%s (%s) CASCADE" % (
                    func[0], func[1], func[2]))
        self.conn.commit()

    def drop(self):
        "Drop the database"
        conn = pgconnect(ADMIN_DB, self.user, self.host, self.port)
        curs = pgexecute_auto(conn, "DROP DATABASE %s" % self.name)
        curs.close()
        conn.close()

    def execute(self, stmt):
        "Execute a DDL statement"
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
        db = Database(DbConnection(self.name, self.user, self.host, self.port))
        return db.to_map()

    def process_map(self, input_map):
        """Process an input map and return the SQL statements necessary to
        convert the database to match the map."""
        db = Database(DbConnection(self.name, self.user, self.host, self.port))
        stmts = db.diff_map(input_map)
        return stmts


class PyrseasTestCase(TestCase):
    """Base class for most test cases"""

    def setUp(self):
        self.db = PostgresDb(TEST_DBNAME, TEST_USER, TEST_HOST, TEST_PORT)
        self.db.connect()
        self.db.clear()

    def tearDown(self):
        self.db.close()
