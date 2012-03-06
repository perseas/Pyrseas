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


def pgconnect(dbname, user, host, port):
    "Connect to a Postgres database using psycopg2"
    if host is None or host == '127.0.0.1' or host == 'localhost':
        host = ''
    else:
        host = 'host=%s ' % host
    if port is None or port == 5432:
        port = ''
    else:
        port = "port=%d " % port
    return connect("%s%sdbname=%s user=%s" % (
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
TEST_HOST = os.environ.get("PYRSEAS_TEST_HOST", None)
TEST_PORT = os.environ.get("PYRSEAS_TEST_PORT", None)
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
        self.port = port and int(port)
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
        # Tables, sequences and views
        curs = pgexecute(
            self.conn,
            """SELECT nspname, relname, relkind FROM pg_class
                      JOIN pg_namespace ON (relnamespace = pg_namespace.oid)
                      JOIN pg_roles ON (nspowner = pg_roles.oid)
               WHERE relkind in ('r', 'S', 'v', 'f')
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
            elif obj['relkind'] == 'f':
                self.execute("DROP FOREIGN TABLE %s.%s CASCADE" % (
                        obj[0], obj[1]))
        self.conn.commit()

        # Types (base, composite and enums) and domains
        #
        # TYPEs have to be done before FUNCTIONs because base types depend
        # on functions, and we're using CASCADE. Also, exclude base array
        # types because they depend on the scalar types.
        curs = pgexecute(
            self.conn,
            """SELECT nspname, typname, typtype FROM pg_type t
                      JOIN pg_namespace n ON (typnamespace = n.oid)
               WHERE typtype IN ('b', 'c', 'd', 'e')
                 AND NOT (typtype = 'b' AND typarray = 0)
                 AND nspname NOT IN ('pg_catalog', 'pg_toast',
                     'information_schema')""")
        types = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for typ in types:
            if typ['typtype'] == 'd':
                self.execute("DROP DOMAIN IF EXISTS %s.%s CASCADE" % (
                        typ[0], typ[1]))
            else:
                self.execute("DROP TYPE IF EXISTS %s.%s CASCADE" % (
                        typ[0], typ[1]))
        self.conn.commit()

        # Functions
        curs = pgexecute(
            self.conn,
            """SELECT nspname, p.oid::regprocedure
               FROM pg_proc p JOIN pg_namespace n ON (pronamespace = n.oid)
               WHERE (nspname != 'pg_catalog'
                     AND nspname != 'information_schema')""")
        funcs = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for func in funcs:
            self.execute("DROP FUNCTION IF EXISTS %s.%s CASCADE" % (
                    func[0], func[1]))
        self.conn.commit()

        # Languages
        if self.version < 90000:
            if self.is_plpgsql_installed():
                self.execute_commit("DROP LANGUAGE plpgsql")

        # Operators
        curs = pgexecute(
            self.conn,
            """SELECT nspname, o.oid::regoperator
               FROM pg_operator o JOIN pg_namespace n ON (oprnamespace = n.oid)
               WHERE (nspname != 'pg_catalog'
                     AND nspname != 'information_schema')""")
        opers = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for oper in opers:
            self.execute("DROP OPERATOR IF EXISTS %s.%s CASCADE" % (
                    oper[0], oper[1]))
        self.conn.commit()

        # Operator families
        curs = pgexecute(
            self.conn,
            """SELECT nspname, opfname, amname
               FROM pg_opfamily o JOIN pg_am a ON (opfmethod = a.oid)
                    JOIN pg_namespace n ON (opfnamespace = n.oid)
               WHERE (nspname != 'pg_catalog'
                     AND nspname != 'information_schema')""")
        opfams = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for opfam in opfams:
            self.execute(
                "DROP OPERATOR FAMILY IF EXISTS %s.%s USING %s CASCADE" % (
                    opfam[0], opfam[1], opfam[2]))
        self.conn.commit()

        # Operator classes
        curs = pgexecute(
            self.conn,
            """SELECT nspname, opcname, amname
               FROM pg_opclass o JOIN pg_am a ON (opcmethod = a.oid)
                    JOIN pg_namespace n ON (opcnamespace = n.oid)
               WHERE (nspname != 'pg_catalog'
                     AND nspname != 'information_schema')""")
        opcls = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for opcl in opcls:
            self.execute(
                "DROP OPERATOR CLASS IF EXISTS %s.%s USING %s CASCADE" % (
                    opcl[0], opcl[1], opcl[2]))
        self.conn.commit()

        # Conversions
        curs = pgexecute(
            self.conn,
            """SELECT nspname, conname FROM pg_conversion c
                      JOIN pg_namespace n ON (connamespace = n.oid)
               WHERE (nspname != 'pg_catalog'
                     AND nspname != 'information_schema')""")
        convs = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for cnv in convs:
            self.execute("DROP CONVERSION IF EXISTS %s.%s CASCADE" % (
                    cnv[0], cnv[1]))
        self.conn.commit()

        # User mappings
        curs = pgexecute(
            self.conn,
            """SELECT CASE umuser WHEN 0 THEN 'PUBLIC' ELSE
                  pg_get_userbyid(umuser) END AS username, srvname
               FROM pg_user_mapping u
                  JOIN pg_foreign_server s ON (umserver = s.oid)""")
        umaps = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for ump in umaps:
            self.execute("DROP USER MAPPING IF EXISTS FOR %s SERVER %s" % (
                    ump[0], ump[1]))
        self.conn.commit()

        # Servers
        curs = pgexecute(self.conn, "SELECT srvname FROM pg_foreign_server")
        servs = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for srv in servs:
            self.execute("DROP SERVER IF EXISTS %s CASCADE" % (srv[0]))
        self.conn.commit()

        # Foreign data wrappers
        curs = pgexecute(self.conn,
                         "SELECT fdwname FROM pg_foreign_data_wrapper")
        fdws = curs.fetchall()
        curs.close()
        self.conn.rollback()
        for fdw in fdws:
            self.execute("DROP FOREIGN DATA WRAPPER IF EXISTS %s CASCADE" % (
                    fdw[0]))
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

    def is_plpgsql_installed(self):
        "Is PL/pgSQL installed?"
        curs = pgexecute(self.conn,
                         "SELECT 1 FROM pg_language WHERE lanname = 'plpgsql'")
        row = curs.fetchone()
        curs.close()
        return row and True

    def execute_and_map(self, ddlstmt):
        "Execute a DDL statement, commit, and return a map of the database"
        self.execute(ddlstmt)
        self.conn.commit()
        db = Database(DbConnection(self.name, self.user, host=self.host,
                                   port=self.port))
        return db.to_map()

    def process_map(self, input_map):
        """Process an input map and return the SQL statements necessary to
        convert the database to match the map."""
        db = Database(DbConnection(self.name, self.user, host=self.host,
                                   port=self.port))
        return db.diff_map(input_map)


class PyrseasTestCase(TestCase):
    """Base class for most test cases"""

    def setUp(self):
        self.db = PostgresDb(TEST_DBNAME, TEST_USER, TEST_HOST, TEST_PORT)
        self.db.connect()
        self.db.clear()

    def tearDown(self):
        self.db.close()

    def std_map(self, plpgsql_installed=False):
        "Return a standard public schema map with its description"
        base = {'schema public': {'description': 'standard public schema'}}
        if self.db._version >= 90000 or plpgsql_installed:
            base.update({'language plpgsql': {'trusted': True}})
        if self.db._version >= 90100:
            base['language plpgsql'].update(
                description="PL/pgSQL procedural language")
        return base
