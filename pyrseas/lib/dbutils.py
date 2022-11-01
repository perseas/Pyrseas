# -*- coding: utf-8 -*-
"""Database utility functions and classes

These are primarily to assist in testing Pyrseas, i.e., without having
to depend on the application-level DbConnection.
"""
import os

from psycopg import connect
from psycopg.rows import dict_row


def pgconnect(dbname, user=None, host=None, port=None, autocommit=False):
    "Connect to a Postgres database using psycopg"
    user = '' if user is None else " user=%s" % user
    host = '' if host is None else "host=%s " % host
    port = '' if port is None else "port=%d " % port
    return connect("%s%sdbname=%s%s" % (host, port, dbname, user),
                   row_factory=dict_row, autocommit=autocommit)


def pgexecute(dbconn, oper, args=None):
    "Execute an operation using a cursor"
    curs = dbconn.cursor()
    try:
        curs.execute(oper, args)
    except:
        curs.close()
        dbconn.rollback()
        raise
    return curs


ADMIN_DB = os.environ.get("PG_ADMIN_DB", 'postgres')
CREATE_DDL = "CREATE DATABASE %s TEMPLATE = template0"


class PostgresDb(object):
    """A PostgreSQL database connection

    This is separate from the one used by DbConnection, because tests
    need to create and drop databases and other objects,
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
                conn2 = pgconnect(ADMIN_DB, self.user, self.host, self.port,
                                  autocommit=True)
                curs = pgexecute(conn2, CREATE_DDL % self.name)
                curs.close()
            conn.close()
            self.conn = pgconnect(self.name, self.user, self.host, self.port)
            curs = pgexecute(self.conn, "SHOW server_version_num")
            vers = curs.fetchone()
            self._version = int(vers["server_version_num"])

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
        conn = pgconnect(ADMIN_DB, self.user, self.host, self.port,
                         autocommit=True)
        curs = pgexecute(conn, "DROP DATABASE IF EXISTS %s" % self.name)
        curs = pgexecute(conn, CREATE_DDL % self.name)
        curs.close()
        conn.close()

    def drop(self):
        "Drop the database"
        conn = pgconnect(ADMIN_DB, self.user, self.host, self.port,
                         autocommit=True)
        curs = pgexecute(conn, "DROP DATABASE %s" % self.name)
        curs.close()
        conn.close()

    def execute(self, stmt, args=None):
        "Execute a DDL statement"
        curs = pgexecute(self.conn, stmt, args)
        curs.close()

    def execute_commit(self, stmt, args=None):
        "Execute a DDL statement and commit"
        self.execute(stmt, args)
        self.conn.commit()

    def fetchone(self, query, args=None):
        "Execute a query and return one row"
        try:
            curs = pgexecute(self.conn, query, args)
        except Exception as exc:
            raise exc
        row = curs.fetchone()
        curs.close()
        return row
