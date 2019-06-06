# -*- coding: utf-8 -*-
"""Test Attributes"""

import os
import pytest

from pyrseas.lib.dbconn import DbConnection


TEST_DBNAME = os.environ.get("PGDBCONN_TEST_DB", "pgdbconn_testdb")


def test_create_dbconn():
    "Create the DbConnection object without connecting"
    db = DbConnection('postgres')
    assert db.conn is None
    assert db.dbname == 'postgres'
    assert db.host == ''
    assert db.user == ''
    assert db.port == ''


def test_create_with_args():
    "Create the DbConnection object with various arguments"
    db = DbConnection('postgres', user='testuser', pswd='testpswd', port=5433)
    assert db.conn is None
    assert db.user == ' user=testuser'
    assert db.pswd == ' password=testpswd'
    assert db.port == 'port=5433 '


def test_connect():
    "Connect to database and fetch the version number"
    db = DbConnection('postgres')
    vers = db.fetchone("SELECT * FROM version()")[0]
    assert db.conn is not None
    assert vers.startswith('PostgreSQL')
    db.close()
    assert db.conn is None


def test_connect_invalid():
    "Connect to a non-existent database"
    db = DbConnection('a_non_existent_database')
    with pytest.raises(SystemExit):
        db.fetchone("SELECT * FROM version()")
    assert db.conn is None


def test_update_database():
    "Create a table, populate it, fetch from it and drop it"
    db = DbConnection(TEST_DBNAME)
    assert db.dbname == TEST_DBNAME
    db.execute("DROP TABLE IF EXISTS test_table")
    db.execute("CREATE TABLE test_table (c1 integer, c2 text)")
    db.commit()
    for i in range(1, 9):
        db.execute("INSERT INTO test_table VALUES (%s, %s)", (i, "A"*i))
    rows = db.fetchall("SELECT c2 FROM test_table ORDER BY c1")
    assert rows[1][0] == "AA"
    db.rollback()
    assert db.fetchall("SELECT * FROM test_table") == []
    db.execute("DROP TABLE test_table")
    db.commit()
