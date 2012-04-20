# -*- coding: utf-8 -*-
"""
    pyrseas.lib.dbconn
    ~~~~~~~~~~~~~~~~~~

    A `DbConnection` is a helper class representing a connection to a
    PostgreSQL database.
"""
import sys

from psycopg2 import connect
from psycopg2.extras import DictConnection


class DbConnection(object):
    """A database connection, possibly disconnected"""

    def __init__(self, dbname, user=None, pswd=None, host=None, port=None):
        """Initialize the connection information

        :param dbname: database name
        :param user: user name
        :param pswd: user password
        :param host: host name
        :param port: host port number
        """
        self.dbname = dbname
        if user is None:
            self.user = ''
        else:
            self.user = " user=%s" % user
        if pswd is None:
            self.pswd = ''
        else:
            self.pswd = " password=%s" % pswd
        if host is None or host == '127.0.0.1' or host == 'localhost':
            self.host = ''
        else:
            self.host = "host=%s " % host
        if port is None or port == 5432:
            self.port = ''
        else:
            self.port = "port=%d " % port
        self.conn = None

    def connect(self):
        """Connect to the database"""
        try:
            self.conn = connect("%s%sdbname=%s%s%s" % (
                    self.host, self.port, self.dbname, self.user, self.pswd),
                                connection_factory=DictConnection)
        except Exception as exc:
            if str(exc)[:6] == 'FATAL:':
                sys.exit("Database connection error: %s" % str(exc)[8:])
            else:
                raise exc

    def close(self):
        """Close the database connection"""
        if self.conn and not self.conn.closed:
            self.conn.close()
        self.conn = None

    def commit(self):
        """Commit currently open transaction"""
        self.conn.commit()

    def rollback(self):
        """Roll back currently open transaction"""
        self.conn.rollback()

    def execute(self, query, args=None):
        """Create a cursor, execute a query and return the cursor

        :param query: text of the statement to execute
        :param args: arguments to query
        :return: cursor
        """
        if self.conn is None or self.conn.closed:
            self.connect()
        curs = self.conn.cursor()
        try:
            curs.execute(query, args)
        except Exception as exc:
            self.conn.rollback()
            curs.close()
            raise exc
        return curs

    def fetchone(self, query, args=None):
        """Execute a single row SELECT query and return row

        :param query: a SELECT query to be executed
        :param args: arguments to query
        :return: a psycopg2 DictRow

        The cursor is closed.
        """
        curs = self.execute(query, args)
        row = curs.fetchone()
        curs.close()
        return row

    def fetchall(self, query, args=None):
        """Execute a SELECT query and return rows

        :param query: a SELECT query to be executed
        :param args: arguments to query
        :return: a list of psycopg2 DictRow's

        The cursor is closed.
        """
        curs = self.execute(query, args)
        rows = curs.fetchall()
        curs.close()
        return rows
