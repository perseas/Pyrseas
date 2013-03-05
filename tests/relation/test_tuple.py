# -*- coding: utf-8 -*-
"""Test Tuples"""
from pytest import raises

from pyrseas.relation import Attribute, Tuple
from pyrseas.relation.tuple import tuple_values_dict


def test_tuple_no_attribs():
    "Create a tuple with no attributes"
    tup = Tuple([])
    assert tup._heading == ()


def test_tuple_one_attrib():
    "Create a tuple with one attribute"
    tup = Tuple(Attribute('attr1'))
    assert tup.attr1 == ''
    assert tup._heading == (('attr1', str), )


def test_tuple_one_attrib_value():
    "Create a tuple with an attribute with a specified value"
    tup = Tuple(Attribute('attr1', int, 123))
    assert tup.attr1 == 123
    assert tup._heading == (('attr1', int), )


def test_tuple_multiple_attribs():
    "Create a tuple with multiple attributes"
    tup = Tuple([Attribute('attr1', int, 123), Attribute('attr2', str, 'abc'),
                 Attribute('attr3', float, 45.67)])
    assert tup.attr1 == 123
    assert tup.attr2 == 'abc'
    assert tup.attr3 == 45.67
    assert tup._sysdefault_attribs == []
    assert tup._nullable_attribs == []
    assert tup._tuple_version is None
    assert tup._heading == (('attr1', int), ('attr2', str), ('attr3', float))
    assert repr(tup) == "Tuple(attr1 int, attr2 str, attr3 float)"


def test_tuple_nullable_attribs():
    "Create a tuple with nullable attributes"
    tup = Tuple([Attribute('attr1', int, 123, nullable=True),
                 Attribute('attr2', str, 'abc'),
                 Attribute('attr3', float, 45.67, nullable=True)])
    assert tup._nullable_attribs == ['attr1', 'attr3']


def test_tuple_nullable_values():
    "Test attributes with nullable values"
    tup = Tuple([Attribute('attr1', int, 123),
                 Attribute('attr2', str, '', nullable=True),
                 Attribute('attr3', int, nullable=True)])
    assert tup.attr2 is None
    assert tup.attr3 is None


def test_tuple_sysdefault_attrib():
    "Create a tuple with a system default attribute"
    tup = Tuple([Attribute('attr1', int, sysdefault=True),
                 Attribute('attr2', str, 'abc')])
    assert tup.attr1 == 0
    assert tup._sysdefault_attribs == ['attr1']


def test_tuple_disallowed_name():
    "Test attribute names don't use internal Tuple attribute/method names"
    with raises(AssertionError):
        Tuple([Attribute('_heading', int, 123)])


def test_tuple_set_reserved_name():
    "Test reserved attributes cannot be set except for _tuple_version"
    tup = Tuple([Attribute('attr1', int, 123)])
    with raises(AssertionError):
        tup._heading = ['abc']
    tup._tuple_version = '1234567'
    assert tup._tuple_version == '1234567'


def test_tuple_set_unknown_attribute():
    "Test unknown attribute cannot be set"
    tup = Tuple([Attribute('attr1', int, 123)])
    with raises(AttributeError):
        tup.attr2 = 234


def test_tuple_set_attribute():
    tup = Tuple([Attribute('attr1', int, 123)])
    tup.attr1 = 456
    assert tup.attr1 == 456


def test_tuple_set_attribute_value_error():
    tup = Tuple([Attribute('attr1', int, 123)])
    with raises(ValueError):
        tup.attr1 = 'abc'


def test_tuple_set_nullable_attribute():
    tup = Tuple([Attribute('attr1', int, 123, nullable=True)])
    tup.attr1 = 0
    assert tup.attr1 is None


def test_tuple_values_dict():
    "Test tuple_values_dict function"
    tup = Tuple([Attribute('attr1', int, 123), Attribute('attr2', str, 'abc'),
                 Attribute('attr3', float, 45.67)])
    assert tuple_values_dict(tup) == {'attr1': 123, 'attr2': 'abc',
                                      'attr3': 45.67}


def test_tuple_changed_values_dict():
    "Test tuple_values_dict with second tuple"
    tup1 = Tuple([Attribute('attr1', int, 123), Attribute('attr2', str, 'abc'),
                  Attribute('attr3', float, 45.67)])
    tup2 = Tuple([Attribute('attr1', int, 123), Attribute('attr2', str, 'def'),
                  Attribute('attr3', float, 98.76),
                  Attribute('attr4', str, 'xyz')])
    assert tuple_values_dict(tup1, tup2) == {'attr2': 'def', 'attr3': 98.76,
                                             'attr4': 'xyz'}


def test_tuple_changed_nullable_values():
    "Test tuple_values_dict with changed nullable values"
    tup1 = Tuple([Attribute('attr1', int, 123), Attribute('attr2', str, 'abc'),
                 Attribute('attr3', float, 45.67)])
    tup2 = Tuple([Attribute('attr1', int, 123),
                  Attribute('attr2', str, '', nullable=True),
                 Attribute('attr3', float, 0, nullable=True)])
    assert tuple_values_dict(tup1, tup2) == {'attr2': None, 'attr3': None}
