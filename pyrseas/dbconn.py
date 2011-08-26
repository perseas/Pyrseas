# -*- coding: utf-8 -*-
"""
    pyrseas.dbconn
    ~~~~~~~~~~~~~~

    A `DbConnection` is a helper class representing a connection to a
    PostgreSQL database.
"""

import os

from psycopg2 import connect
from psycopg2.extras import DictConnection


class DbConnection(object):
    """A database connection, possibly disconnected"""

    def __init__(self, dbname, user=None, host=None, port=None):
        """Initialize the connection information

        :param dbname: database name
        :param user: user name
        :param host: host name
        :param port: host port number
        """
        self.dbname = dbname
        self.user = user
        if host is None or host == '127.0.0.1' or host == 'localhost':
            self.host = ''
        else:
            self.host = "host=%s " % host
        if port is None or port == 5432:
            self.port = ''
        else:
            self.port = "port=%d " % port
        self.conn = None
        self._version = 0

    def connect(self):
        """Connect to the database

        If user is None, the USER environment variable is used
        instead. The password is either not required or supplied by
        other means, e.g., a $HOME/.pgpass file.
        """
        self.conn = connect("%s%sdbname=%s user=%s" % (
                self.host, self.port, self.dbname,
                self.user or os.getenv("USER")),
                            connection_factory=DictConnection)
        try:
            self._execute("set search_path to public, pg_catalog")
        except:
            self.conn.rollback()
            self._execute("set search_path to pg_catalog")
        self._version = int(self.fetchone("SHOW server_version_num")[0])

    def _execute(self, query):
        """Create a cursor, execute a query and return the cursor"""
        curs = self.conn.cursor()
        try:
            curs.execute(query)
        except Exception, exc:
            exc.args += (query, )
            raise
        return curs

    def fetchone(self, query):
        """Execute a single row SELECT query and return data

        :param query: a SELECT query to be executed
        :return: a psycopg2 DictRow

        The cursor is closed and a rollback is issued.
        """
        curs = self._execute(query)
        data = curs.fetchone()
        curs.close()
        self.conn.rollback()
        return data

    def fetchall(self, query):
        """Execute a SELECT query and return data

        :param query: a SELECT query to be executed
        :return: a list of psycopg2 DictRow's

        The cursor is closed and a rollback is issued.
        """
        curs = self._execute(query)
        data = curs.fetchall()
        curs.close()
        self.conn.rollback()
        return data

    @property
    def version(self):
        "The server's version number"
        return self._version
