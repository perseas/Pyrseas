# -*- coding: utf-8 -*-
"""Pyrseas unit tests"""

import unittest

from tests.dbobject import test_language
from tests.dbobject import test_cast
from tests.dbobject import test_schema
from tests.dbobject import test_type
from tests.dbobject import test_domain
from tests.dbobject import test_sequence
from tests.dbobject import test_table
from tests.dbobject import test_column
from tests.dbobject import test_constraint
from tests.dbobject import test_index
from tests.dbobject import test_view
from tests.dbobject import test_function
from tests.dbobject import test_operator
from tests.dbobject import test_operfamily
from tests.dbobject import test_operclass
from tests.dbobject import test_trigger
from tests.dbobject import test_rule
from tests.dbobject import test_conversion
from tests.dbobject import test_textsearch
from tests.dbobject import test_foreign
from tests.dbobject import test_extension
from tests.dbobject import test_tablespace
from tests.dbobject import test_collation
from tests.dbobject import test_owner
from tests.dbobject import test_privs


def suite():
    tests = unittest.TestSuite()
    tests.addTest(test_language.suite())
    tests.addTest(test_cast.suite())
    tests.addTest(test_schema.suite())
    tests.addTest(test_type.suite())
    tests.addTest(test_domain.suite())
    tests.addTest(test_sequence.suite())
    tests.addTest(test_table.suite())
    tests.addTest(test_column.suite())
    tests.addTest(test_constraint.suite())
    tests.addTest(test_index.suite())
    tests.addTest(test_view.suite())
    tests.addTest(test_function.suite())
    tests.addTest(test_operator.suite())
    tests.addTest(test_operfamily.suite())
    tests.addTest(test_operclass.suite())
    tests.addTest(test_trigger.suite())
    tests.addTest(test_rule.suite())
    tests.addTest(test_conversion.suite())
    tests.addTest(test_textsearch.suite())
    tests.addTest(test_foreign.suite())
    tests.addTest(test_extension.suite())
    tests.addTest(test_tablespace.suite())
    tests.addTest(test_collation.suite())
    tests.addTest(test_owner.suite())
    tests.addTest(test_privs.suite())
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
