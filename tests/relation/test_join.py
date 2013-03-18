# -*- coding: utf-8 -*-
"""Test JoinRelations"""

import pytest

from pyrseas.relation import ProjAttribute, Projection, JoinRelation
from pyrseas.testutils import RelationTestCase

pr1 = Projection('arv', [ProjAttribute('a_id', int),
                         ProjAttribute('title'),
                         ProjAttribute('descr', nullable=True),
                         ProjAttribute('code', int)])

pr2 = Projection('arv', [ProjAttribute('title')])

pr3 = Projection('brv', [ProjAttribute('num', int),
                         ProjAttribute('name'),
                         ProjAttribute('a_id', int)])

jr1 = JoinRelation([pr1])
jr2 = JoinRelation([pr3, pr2], join="NATURAL JOIN arv a", extname='b_and_a')
jr3 = JoinRelation(
    [Projection('crv',
                [ProjAttribute('parent_id', int, basename='id1'),
                 ProjAttribute('code', int),
                 ProjAttribute('child_id', int, basename='id2')],
                rangevar='r'),
     Projection('arv',
                [ProjAttribute('parent_name', basename='name')],
                rangevar='p'),
     Projection('arv',
                [ProjAttribute('child_name', basename='name')],
                rangevar='c')],
    join="JOIN arv p ON (id1 = p.id) JOIN arv c ON (id2 = c.id)")


@pytest.fixture
def proj1(request):
    return pr1


@pytest.fixture
def joinrel1(request):
    return jr1


@pytest.fixture
def joinrel2(request):
    return jr2


@pytest.fixture
def joinrel3(request):
    return jr3


def test_projection(proj1):
    "Create a projection of a single relvar"
    assert proj1.rvname == 'arv'
    attr0 = proj1.attributes[0]
    assert attr0[0] == 'a_id'
    assert attr0[1].name == 'a_id'
    assert attr0[1].type == int
    assert attr0[1].nullable is False
    assert attr0[1].sysdefault is False
    assert attr0[1].basename == 'a_id'
    assert attr0[1].projection == proj1
    attr1 = proj1.attributes[1]
    assert attr1[0] == 'title'
    assert attr1[1].name == 'title'
    assert attr1[1].type == str
    attr2 = proj1.attributes[2]
    assert attr2[0] == 'descr'
    assert attr2[1].name == 'descr'
    assert attr2[1].type == str
    attr3 = proj1.attributes[3]
    assert attr3[0] == 'code'
    assert attr3[1].name == 'code'
    assert attr3[1].type == int
    assert proj1.rangevar == 'a'


def test_joinrel_single(joinrel1):
    "Create a join relation from a single projection"
    assert joinrel1.extname == 'arv'
    attr0 = joinrel1.attributes[0]
    assert attr0[1].name == 'a_id'
    assert attr0[1].type == int
    attr1 = joinrel1.attributes[1]
    assert attr1[0] == 'title'
    assert attr1[1].name == 'title'
    assert attr1[1].type == str
    assert joinrel1.from_clause == "arv a"


def test_joinrel_single_tuple_values(joinrel1):
    "Create a tuple for a single projection join from passed-in arguments"
    tup = joinrel1.tuple(1, 'abc', code=987)
    assert tup.a_id == 1
    assert tup.title == 'abc'
    assert tup.code == 987


def test_joinrel_invalid_attribute(joinrel1):
    "Create a tuple based on join relation but with incorrect type"
    with pytest.raises(ValueError):
        joinrel1.tuple(code=12.34)


def test_joinrel_unknown_attribute(joinrel1):
    "Create a tuple with an unknown attribute"
    with pytest.raises(KeyError):
        joinrel1.tuple(name='abc')


def test_joinrel_double(joinrel2):
    "Create a join relation from two projections"
    assert joinrel2.extname == 'b_and_a'
    attr0 = joinrel2.attributes[0]
    assert attr0[0] == 'num'
    assert attr0[1].name == 'num'
    assert attr0[1].type == int
    attr1 = joinrel2.attributes[1]
    assert attr1[0] == 'name'
    assert attr1[1].name == 'name'
    assert attr1[1].type == str
    attr2 = joinrel2.attributes[2]
    assert attr2[0] == 'a_id'
    assert attr2[1].name == 'a_id'
    assert attr2[1].type == int
    assert joinrel2.from_clause == "brv b NATURAL JOIN arv a"


def test_joinrel_three_way(joinrel3):
    "Create a join relation from three projections, two on the same relvar"
    assert joinrel3.extname == 'crv'
    attr0 = joinrel3.attributes[0]
    assert attr0[0] == 'parent_id'
    assert attr0[1].type == int
    assert attr0[1].basename == 'id1'
    attr1 = joinrel3.attributes[1]
    assert attr1[0] == 'code'
    assert attr1[1].type == int
    assert attr1[1].basename == 'code'
    attr2 = joinrel3.attributes[2]
    assert attr2[0] == 'child_id'
    assert attr2[1].type == int
    assert attr2[1].basename == 'id2'
    attr3 = joinrel3.attributes[3]
    assert attr3[0] == 'parent_name'
    assert attr3[1].type == str
    assert attr3[1].basename == 'name'
    attr4 = joinrel3.attributes[4]
    assert attr4[0] == 'child_name'
    assert attr4[1].type == str
    assert attr4[1].basename == 'name'
    assert joinrel3.from_clause == "crv r JOIN arv p ON (id1 = p.id) " \
        "JOIN arv c ON (id2 = c.id)"


def test_joinrel_dupe_rangevar(proj1):
    "Create a join relation with a duplicate rangevar"
    with pytest.raises(ValueError):
        JoinRelation([proj1, Projection('rv', [ProjAttribute('name')],
                                        rangevar='a')])


class TestJoinRel1(RelationTestCase):

    @pytest.fixture(autouse=True)
    def setup(self):
        self.relation = jr1
        self.relation.connect(self.db)
        self.pgdb.execute("DROP TABLE IF EXISTS arv CASCADE")
        self.pgdb.execute_commit(
            "CREATE TABLE arv (a_id integer PRIMARY KEY, "
            "title text NOT NULL, descr text, code integer NOT NULL)")

    def insert_multiple(self, count):
        self.pgdb.execute_commit(
            "INSERT INTO arv SELECT i, 'Title ' || i, 'Description ' || i, "
            "(i %% 3) + 1 FROM generate_series(1, %d) i" % count)

    def test_joinrel_get_several(self):
        "Get several tuples"
        self.insert_multiple(3)
        tuples = self.relation.subset()
        assert len(tuples) == 3
        assert tuples[0].a_id == 1
        assert tuples[0].title == 'Title 1'
        assert tuples[2].descr == 'Description 3'
        assert tuples[2].code == 1

    def test_joinrel_get_none(self):
        "Get several tuples but find none"
        assert len(self.relation.subset()) == 0

    def test_joinrel_get_slice(self):
        "Get a slice of tuples"
        self.insert_multiple(100)
        assert self.relation.count() == 100
        tuples = self.relation.subset(10, 30)
        assert len(tuples) == 10
        assert tuples[0].title == 'Title 31'
        assert tuples[9].code == 2

    def test_joinrel_search(self):
        "Get a subset of tuples by searching by title"
        self.insert_multiple(100)
        tuples = self.relation.subset(qry_args={'title': '7'})
        assert len(tuples) == 19
        assert tuples[2].title == 'Title 27'


class TestJoinRel2(RelationTestCase):

    @pytest.fixture(autouse=True)
    def setup(self):
        self.relation = jr2
        self.relation.connect(self.db)
        self.pgdb.execute("DROP TABLE IF EXISTS arv, brv CASCADE")
        self.pgdb.execute(
            "CREATE TABLE arv (a_id integer PRIMARY KEY, title text NOT NULL)")
        self.pgdb.execute(
            "CREATE TABLE brv (num integer PRIMARY KEY, name text NOT NULL, "
            "a_id integer NOT NULL REFERENCES arv (a_id))")
        self.pgdb.execute("INSERT INTO arv VALUES (1, 'John Doe'), "
                          "(2, 'Bob Smith'), (3, 'Peter Jones')")
        self.pgdb.execute_commit(
            "INSERT INTO brv SELECT i, 'Name ' || i, (i % 3) + 1 "
            "FROM generate_series(1, 100) i")

    def test_get_join_slice(self):
        "Get a slice of tuples from a join"
        assert self.relation.count() == 100
        tuples = self.relation.subset(10, 30)
        assert len(tuples) == 10
        assert tuples[0].name == 'Name 31'
        assert tuples[9].title == 'Bob Smith'

    def test_get_join_slice_order(self):
        "Get a slice of tuples from a join ordered by different attribute"
        tuples = self.relation.subset(10, 30, order=['title'])
        assert tuples[0].title == 'Bob Smith'
        assert tuples[9].title == 'John Doe'

    def test_get_join_slice_order_desc(self):
        "Get a slice of tuples from a join ordered DESCending"
        tuples = self.relation.subset(10, 0, order=['name DESC'])
        assert tuples[0].name == 'Name 99'
        assert tuples[9].title == 'John Doe'

    def test_get_join_order_by_unknown(self):
        "Get a slice of tuples ordered by unknown attribute"
        with pytest.raises(AttributeError):
            self.relation.subset(10, 30, order=['unknown'])

    def test_search_second_proj(self):
        "Get a subset of tuples by attribute of second projection"
        tuples = self.relation.subset(qry_args={'title': 'peter'})
        assert len(tuples) == 33

    def test_search_numeric_greater(self):
        "Get a subset of tuples by using greater than on integer attribute"
        tuples = self.relation.subset(qry_args={'num': '> 50'})
        assert len(tuples) == 50

    def test_search_two_args(self):
        "Get a subset of tuples by using two search attributes"
        tuples = self.relation.subset(qry_args={'title': 'peter',
                                                'num': '> 50'})
        assert len(tuples) == 16
        assert tuples[0].num == 53
        assert tuples[0].title == 'Peter Jones'
        assert tuples[15].num == 98


class TestJoinRel3(RelationTestCase):

    @pytest.fixture(autouse=True)
    def setup(self):
        self.relation = jr3
        self.relation.connect(self.db)
        self.pgdb.execute("DROP TABLE IF EXISTS arv, crv CASCADE")
        self.pgdb.execute(
            "CREATE TABLE arv (id integer PRIMARY KEY, name text NOT NULL)")
        self.pgdb.execute(
            "CREATE TABLE crv (id1 integer NOT NULL REFERENCES arv (id), "
            "id2 integer NOT NULL REFERENCES arv (id), "
            "code integer NOT NULL, PRIMARY KEY (id1, code, id2))")
        self.pgdb.execute(
            "INSERT INTO arv VALUES (1, 'John Doe'), (2, 'Bob Smith')")
        self.pgdb.execute(
            "INSERT INTO crv SELECT 1, 2, i FROM generate_series(11, 60) i")
        self.pgdb.execute_commit(
            "INSERT INTO crv SELECT 2, 1, i FROM generate_series(31, 80) i")

    def test_search_three_way(self):
        "Get a subset of tuple by parent_name"
        tuples = self.relation.subset(qry_args={'parent_name': 'Bob'},
                                      order=['parent_name', 'code'])
        assert len(tuples) == 50
        assert tuples[0].parent_name == 'Bob Smith'
        assert tuples[0].child_name == 'John Doe'
        assert tuples[0].code == 31
        assert tuples[49].code == 80
