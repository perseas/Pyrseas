# -*- coding: utf-8 -*-
"""Test languages"""

import psycopg

from pyrseas.testutils import DatabaseToMapTestCase


class LanguageToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of existing languages"""

    def test_map_language_bug_103(self):
        "Test a function created with language other than plpgsql/plperl"
        if self.db.version >= 130000:
            self.skipTest('Only available before PG 13')
        try:
            self.to_map(["CREATE OR REPLACE LANGUAGE plpython3u"])
        except psycopg.OperationalError as e:
            self.skipTest("plpython3 installation failed: %s" % e)
        m = self.to_map(["CREATE FUNCTION test103() RETURNS int AS "
                         "'return 1' LANGUAGE plpython3u"])
        self.to_map(["DROP LANGUAGE plpython3u CASCADE"])
        assert 'language plpython3u' in m
