# -*- coding: utf-8 -*-
"""Test RelVars"""
from copy import copy
from datetime import date, datetime, timedelta

import pytest
from psycopg2 import DatabaseError, IntegrityError

from pyrseas.relation import RelVar, Attribute
from pyrseas.testutils import RelationTestCase

TEST_DATA1 = {'title': "John Doe"}
TEST_DATA1x = {'id': 2, 'title': "Bob Smith"}
TEST_DATA2 = {'num': 123, 'name': "Name 1", 'id': 1}
TEST_DATA3 = {'id1': 1, 'id2': 2, 'code': 'ES', 'descr': 'Una descripción'}


rv1 = RelVar('rv1', [Attribute('id', int, sysdefault=True),
                     Attribute('title'),
                     Attribute('descr', nullable=True),
                     Attribute('updated', datetime, sysdefault=True)],
             key=['id'])

rv2 = RelVar('rv2', [Attribute('num', int), Attribute('name'),
                     Attribute('id', int)], key=['num'])

rv3 = RelVar('rv3', [Attribute('id1', int), Attribute('id2', int),
                     Attribute('code'), Attribute('descr'),
                     Attribute('created', date, sysdefault=True)],
             key=['id1', 'code', 'id2'])


@pytest.fixture
def relvar1(request):
    return rv1


def test_relvar_default_tuple(relvar1):
    "Create a tuple with default (blank) values"
    tup = relvar1.default_tuple()
    assert tup.id == 0
    assert tup.title == ''


def test_relvar_tuple_values(relvar1):
    "Create a tuple based on relvar and passed-in arguments"
    tup = relvar1.tuple(**TEST_DATA1)
    assert tup.title == TEST_DATA1['title']
    assert tup._heading == (('title', str), )


def test_relvar_invalid_attribute(relvar1):
    "Create a tuple based on relvar but with incorrect type"
    with pytest.raises(ValueError):
        relvar1.tuple(title=12.34)


def test_relvar_tuple_missing_required(relvar1):
    "Create a tuple without a required attribute"
    with pytest.raises(ValueError):
        relvar1.tuple(1)


def test_relvar_tuple_unknown_attribute(relvar1):
    "Create a tuple with an unknown attribute"
    with pytest.raises(KeyError):
        relvar1.tuple(code='abc')


class TestRelvar1(RelationTestCase):

    @pytest.fixture(autouse=True)
    def setup(self):
        self.relvar = rv1
        self.relvar.connect(self.db)
        self.pgdb.execute("DROP TABLE IF EXISTS rv1 CASCADE")
        self.pgdb.execute_commit(
            "CREATE TABLE rv1 (id serial PRIMARY KEY, "
            "title text NOT NULL UNIQUE, descr text, "
            "updated timestamp with time zone DEFAULT CURRENT_TIMESTAMP)")

    def insert_one(self):
        self.pgdb.execute_commit("INSERT INTO rv1 (title) VALUES (%(title)s)",
                                 (TEST_DATA1))

    def delete_one(self, id):
        self.pgdb.execute_commit("DELETE FROM rv1 WHERE id = %s", (id,))

    def get_one(self, id):
        return self.pgdb.fetchone("SELECT xmin, * FROM rv1 WHERE id = %s",
                                  (id,))

    def test_relvar_insert_one_serial(self):
        "Insert a tuple into a relvar with a sequenced primary key"
        newtuple = self.relvar.tuple(**TEST_DATA1)
        self.relvar.insert_one(newtuple)
        now = datetime.now()
        self.db.commit()
        row = self.get_one(1)
        assert row['title'] == newtuple.title
        assert (now - row['updated'].replace(tzinfo=None)) < timedelta(0, 1)

    def test_relvar_insert_one_override_pk(self):
        "Insert a tuple but override normal sequenced primary key value"
        data = TEST_DATA1.copy()
        data['id'] = 123
        newtuple = self.relvar.tuple(**data)
        self.relvar.insert_one(newtuple)
        self.db.commit()
        row = self.get_one(123)
        assert row['title'] == newtuple.title

    def test_relvar_insert_one_serial_return_pk(self):
        "Insert a tuple and return the generated primary key value"
        self.insert_one()
        newtuple = self.relvar.tuple(title=TEST_DATA1x['title'])
        retval = self.relvar.insert_one(newtuple, True)
        self.db.commit()
        row = self.get_one(retval.id)
        assert row['title'] == newtuple.title

    def test_relvar_insert_one_nullables(self):
        "Insert a tuple with nullable attributes as blanks"
        data = TEST_DATA1.copy()
        data['descr'] = ''
        newtuple = self.relvar.tuple(**data)
        self.relvar.insert_one(newtuple)
        self.db.commit()
        row = self.get_one(1)
        assert row['descr'] is None

    def test_relvar_dup_insert_pk(self):
        "Insert a duplicate by overriding normal sequenced primary key value"
        self.insert_one()
        data = TEST_DATA1.copy()
        data['id'] = 1
        newtuple = self.relvar.tuple(**data)
        with pytest.raises(IntegrityError):
            self.relvar.insert_one(newtuple)

    def test_relvar_dup_insert_alt_key(self):
        "Insert a duplicate on a unique attribute"
        self.insert_one()
        newtuple = self.relvar.tuple(**TEST_DATA1)
        with pytest.raises(IntegrityError):
            self.relvar.insert_one(newtuple)

    def test_relvar_get_one(self):
        "Retrieve a single tuple from a relvar"
        self.insert_one()
        now = datetime.now()
        currtuple = self.relvar.get_one(self.relvar.key_tuple(1))
        assert currtuple.id == 1
        assert currtuple.title == TEST_DATA1['title']
        assert (now - currtuple.updated.replace(tzinfo=None)) < timedelta(0, 1)

    def test_relvar_get_one_fail(self):
        "Fail to retrieve a single tuple from a relvar"
        assert self.relvar.get_one(self.relvar.key_tuple(1)) is None

    def test_relvar_update_one(self):
        "Update a single tuple in a relvar"
        self.insert_one()
        keytuple = self.relvar.key_tuple(1)
        currtuple = self.relvar.get_one(keytuple)
        currtuple.title = "Jane Doe"
        currtuple.updated = datetime.now()
        self.relvar.update_one(currtuple, keytuple)
        self.db.commit()
        row = self.get_one(1)
        assert row['title'] == currtuple.title
        assert row['updated'].replace(tzinfo=None) == currtuple.updated

    def test_relvar_update_one_from_current(self):
        "Update a single tuple from a fetched tuple"
        self.insert_one()
        keytuple = self.relvar.key_tuple(1)
        currtuple = self.relvar.get_one(keytuple)
        newtuple = copy(currtuple)
        newtuple.title = "Jane Doe"
        newtuple.updated = datetime.now()
        self.relvar.update_one(newtuple, keytuple, currtuple)
        self.db.commit()
        row = self.get_one(1)
        assert row['title'] == newtuple.title
        assert row['xmin'] != newtuple._tuple_version
        assert row['updated'].replace(tzinfo=None) == newtuple.updated

    def test_relvar_update_one_no_change(self):
        "Update a single tuple but without really changing anything"
        self.insert_one()
        keytuple = self.relvar.key_tuple(1)
        currtuple = self.relvar.get_one(keytuple)
        newtuple = copy(currtuple)
        newtuple.title = "John Doe"
        self.relvar.update_one(newtuple, keytuple, currtuple)
        self.db.commit()
        row = self.get_one(1)
        assert row['title'] == newtuple.title
        assert row['xmin'] == newtuple._tuple_version

    def test_relvar_update_missing(self):
        "Attempt to update a tuple that has been deleted since it was fetched"
        self.insert_one()
        keytuple = self.relvar.key_tuple(1)
        currtuple = self.relvar.get_one(keytuple)
        currtuple.title = "Jane Doe"
        self.delete_one(1)
        with pytest.raises(DatabaseError):
            self.relvar.update_one(currtuple, keytuple)

    def test_relvar_delete_one(self):
        "Delete a single tuple from a relvar"
        self.insert_one()
        keytuple = self.relvar.key_tuple(1)
        currtuple = self.relvar.get_one(keytuple)
        self.relvar.delete_one(keytuple, currtuple)
        self.db.commit()
        assert self.get_one(1) is None

    def test_relvar_delete_missing(self):
        "Attempt to delete a tuple that has been deleted since it was fetched"
        self.insert_one()
        keytuple = self.relvar.key_tuple(1)
        currtuple = self.relvar.get_one(keytuple)
        self.delete_one(1)
        with pytest.raises(DatabaseError):
            self.relvar.delete_one(currtuple, keytuple)


class TestRelvar2(RelationTestCase):

    @pytest.fixture(autouse=True)
    def setup(self):
        self.relvar = rv2
        self.relvar.connect(self.db)
        self.pgdb.execute("DROP TABLE IF EXISTS rv2, rv1 CASCADE")
        self.pgdb.execute("CREATE TABLE rv1 (id integer PRIMARY KEY, "
                          "title text NOT NULL)")
        self.pgdb.execute("CREATE TABLE rv2 (num integer PRIMARY KEY, "
                          "name text NOT NULL, "
                          "id integer NOT NULL REFERENCES rv1 (id))")
        self.pgdb.execute_commit("INSERT INTO rv1 VALUES (1, %(title)s)",
                                 (TEST_DATA1),)

    def insert_one(self):
        self.pgdb.execute_commit(
            "INSERT INTO rv2 VALUES (%(num)s, %(name)s, %(id)s)",
            (TEST_DATA2),)

    def get_one(self, num):
        return self.pgdb.fetchone("SELECT xmin, * FROM rv2 WHERE num = %s",
                                  (num,))

    def test_relvar_insert_fk(self):
        "Insert a tuple into a relvar that references another"
        # This also tests insert into non-sequenced primary key
        newtuple = self.relvar.tuple(**TEST_DATA2)
        self.relvar.insert_one(newtuple)
        self.db.commit()
        row = self.get_one(123)
        assert row['name'] == newtuple.name
        assert row['id'] == newtuple.id

    def test_relvar_dup_insert(self):
        "Insert a duplicate primary key value"
        self.insert_one()
        newtuple = self.relvar.tuple(**TEST_DATA2)
        with pytest.raises(IntegrityError):
            self.relvar.insert_one(newtuple)

    def test_relvar_insert_bad_fk(self):
        "Insert a tuple into a relvar with invalid foreign key"
        data = TEST_DATA2.copy()
        data['id'] = 2
        newtuple = self.relvar.tuple(**data)
        with pytest.raises(IntegrityError):
            self.relvar.insert_one(newtuple)

    def test_relvar_update_key(self):
        "Update a tuple's primary key"
        self.insert_one()
        keytuple = self.relvar.key_tuple(123)
        currtuple = self.relvar.get_one(keytuple)
        currtuple.num = 456
        self.relvar.update_one(currtuple, keytuple)
        self.db.commit()
        row = self.get_one(456)
        assert row['num'] == 456
        assert row['name'] == TEST_DATA2['name']
        assert row['id'] == TEST_DATA2['id']

    def test_relvar_update_fk(self):
        "Update a tuple's foreign key"
        self.pgdb.execute_commit("INSERT INTO rv1 VALUES (%(id)s, %(title)s)",
                                 (TEST_DATA1x))
        self.insert_one()
        keytuple = self.relvar.key_tuple(123)
        currtuple = self.relvar.get_one(keytuple)
        currtuple.id = 2
        self.relvar.update_one(currtuple, keytuple)
        self.db.commit()
        row = self.pgdb.fetchone(
            "SELECT title FROM rv1 NATURAL JOIN rv2 WHERE num = 123")
        assert row['title'] == TEST_DATA1x['title']

    def test_relvar_update_fk_fail(self):
        "Update a tuple's foreign key to an unknown value"
        self.pgdb.execute_commit("DELETE FROM rv1 WHERE id = 2")
        self.insert_one()
        keytuple = self.relvar.key_tuple(123)
        currtuple = self.relvar.get_one(keytuple)
        currtuple.id = 2
        with pytest.raises(IntegrityError):
            self.relvar.update_one(currtuple, keytuple)


class TestRelvar3(RelationTestCase):

    @pytest.fixture(autouse=True)
    def setup(self):
        self.relvar = rv3
        self.relvar.connect(self.db)
        self.pgdb.execute("DROP TABLE IF EXISTS rv3, rv1 CASCADE")
        self.pgdb.execute("CREATE TABLE rv1 (id integer PRIMARY KEY, "
                          "title text NOT NULL)")
        self.pgdb.execute(
            "CREATE TABLE rv3 (id1 integer NOT NULL REFERENCES rv1 (id), "
            "id2 integer NOT NULL REFERENCES rv1 (id), "
            "code char(2) NOT NULL, descr text NOT NULL, "
            "created date NOT NULL DEFAULT CURRENT_DATE, "
            "PRIMARY KEY (id1, code, id2))")
        self.pgdb.execute_commit("INSERT INTO rv1 VALUES (1, %(title)s)",
                                 (TEST_DATA1),)
        self.pgdb.execute_commit("INSERT INTO rv1 VALUES (%(id)s, %(title)s)",
                                 (TEST_DATA1x),)

    def insert_one(self):
        self.pgdb.execute_commit(
            "INSERT INTO rv3 VALUES (%(id1)s, %(id2)s, %(code)s, %(descr)s)",
            (TEST_DATA3),)

    def get_one(self, data):
        return self.pgdb.fetchone(
            "SELECT xmin, * FROM rv3 WHERE id1 = %(id1)s AND "
            "id2 = %(id2)s AND code = %(code)s", (data))

    def test_relvar_key_tuple(self):
        "Create a key tuple with both args and keyword args"
        tup = self.relvar.key_tuple(123, code='EN', id2=456)
        assert tup.id1 == 123
        assert tup.code == 'EN'
        assert tup.id2 == 456

    def test_relvar_insert_multi_key(self):
        "Insert a tuple into a relvar with a multi-attribute key"
        newtuple = self.relvar.tuple(**TEST_DATA3)
        self.relvar.insert_one(newtuple)
        self.db.commit()
        row = self.get_one(TEST_DATA3)
        assert row['id1'] == newtuple.id1
        assert row['code'] == newtuple.code
        assert row['id2'] == newtuple.id2
        assert row['descr'] == newtuple.descr
        assert row['created'] == date.today()

    def test_relvar_update_one(self):
        "Update a tuple in a relvar with a multi-attribute key"
        self.insert_one()
        keytuple = self.relvar.key_tuple(**TEST_DATA3)
        currtuple = self.relvar.get_one(keytuple)
        currtuple.code = 'FR'
        currtuple.descr = "Une description"
        self.relvar.update_one(currtuple, keytuple)
        self.db.commit()
        data = TEST_DATA3.copy()
        data['code'] = currtuple.code
        row = self.get_one(data)
        assert row['id1'] == currtuple.id1
        assert row['code'] == currtuple.code
        assert row['id2'] == currtuple.id2
        assert row['descr'] == currtuple.descr
