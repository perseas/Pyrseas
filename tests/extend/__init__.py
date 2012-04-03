# -*- coding: utf-8 -*-
"""Pyrseas extender unit tests"""

import unittest

from tests.extend import test_audit
from tests.extend import test_denorm


def suite():
    tests = unittest.TestSuite()
    tests.addTest(test_audit.suite())
    tests.addTest(test_denorm.suite())
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
