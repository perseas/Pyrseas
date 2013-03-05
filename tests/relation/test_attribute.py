# -*- coding: utf-8 -*-
"""Test Attributes"""
from datetime import date

import pytest

from pyrseas.relation import Attribute


def test_attrib_defaults():
    "Create an attribute with default arguments"
    attr = Attribute('attr1')
    assert attr.name == 'attr1'
    assert attr.type == str
    assert attr.value == ''
    assert attr.nullable is False
    assert attr.sysdefault is False


def test_attrib_value():
    "Create an attribute with a given value"
    attr = Attribute('attr1', int, 123)
    assert attr.type == int
    assert attr.value == 123


def test_attrib_args():
    "Create an attribute with various arguments"
    attr = Attribute('attr1', float, 45.67, sysdefault=True)
    assert attr.name == 'attr1'
    assert attr.type == float
    assert attr.value == 45.67
    assert attr.nullable is False
    assert attr.sysdefault is True
    assert repr(attr) == "Attribute(attr1 float)"


def test_attrib_nullables():
    "Create nullable attributes that should get None as value"
    attr = Attribute('attr1', int, nullable=True)
    assert attr.value is None
    attr = Attribute('attr2', int, 0, nullable=True)
    assert attr.value is None
    attr = Attribute('attr3', str, '', nullable=True)
    assert attr.value is None
    attr = Attribute('attr4', date, nullable=True)
    assert attr.value is None


def test_attrib_value_error():
    "Validate declared type against value type"
    with pytest.raises(ValueError):
        Attribute('attr1', int, 12.34)


def test_attrib_nullable_value_error():
    "Validate declared type against value type for a nullable attribute"
    with pytest.raises(ValueError):
        Attribute('attr1', str, 123, nullable=True)


def test_attrib_not_nullable_no_value():
    "Ensure non-nullable, non-defaultable attribute has a value"
    with pytest.raises(ValueError):
        Attribute('attr1', date)


def test_attrib_not_nullable_sysdefault():
    "Allow non-nullable, system-defaultable attribute to be None"
    attr = Attribute('attr1', date, sysdefault=True)
    assert attr.value is None


def test_attrib_int_is_float():
    "Accept an int value for float type"
    attr = Attribute('attr1', float, 0)
    assert attr.type == float
    assert attr.value == 0.0


@pytest.mark.skipif("sys.version_info >= (3,0)")
def test_attrib_unicode_is_str():
    "Accept str as type synonym for unicode under Python 2"
    val = unicode('A string')
    attr = Attribute('attr1', value=val)
    assert attr.type == str
    assert attr.value == val
