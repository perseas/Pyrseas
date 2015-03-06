# -*- coding: utf-8 -*-
"""Test extensions"""

import pytest

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

CREATE_STMT = "CREATE EXTENSION pg_trgm"
TRGM_COMMENT = "text similarity measurement and index searching based on " \
    "trigrams"


class ExtensionToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of existing extensions"""

    superuser = True

    def test_map_extension(self):
        "Map an existing extension"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        VERS = '1.0' if self.db.version < 90300 else '1.1'
        dbmap = self.to_map([CREATE_STMT])
        assert dbmap['extension pg_trgm'] == {
            'schema': 'public', 'version': VERS, 'description': TRGM_COMMENT}

    def test_map_no_depends(self):
        "Ensure no dependencies are included when mapping an extension"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        dbmap = self.to_map([CREATE_STMT])
        assert 'type gtrgm' not in dbmap['schema public']
        assert not 'operator %(text, text)' in dbmap['schema public']
        assert not 'function show_trgm(text)' in dbmap['schema public']

    def test_map_lang_extension(self):
        "Map a procedural language as an extension"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        dbmap = self.to_map(["CREATE EXTENSION plperl"])
        assert dbmap['extension plperl'] == {
            'schema': 'pg_catalog', 'version': '1.0',
            'description': "PL/Perl procedural language"}
        assert not 'language plperl' in dbmap

    def test_map_extension_schema(self):
        "Map an existing extension"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        VERS = '1.0' if self.db.version < 90300 else '1.1'
        dbmap = self.to_map(["CREATE SCHEMA s1", CREATE_STMT + " SCHEMA s1"])
        assert dbmap['extension pg_trgm'] == {
            'schema': 's1', 'version': VERS, 'description': TRGM_COMMENT}

    def test_map_extension_bug_103(self):
        "Test a function created with extension other than plpgsql/plperl"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        dbmap = self.to_map(["CREATE EXTENSION plpythonu",
                             "CREATE FUNCTION test103() RETURNS int AS "
                             "'return 1' LANGUAGE plpythonu"])
        assert 'extension plpythonu' in dbmap


class ExtensionToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation for input extensions"""

    def test_create_extension(self):
        "Create a extension that didn't exist"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        inmap = self.std_map()
        inmap.update({'extension pg_trgm': {'schema': 'public'}})
        sql = self.to_sql(inmap)
        assert sql == [CREATE_STMT]

    def test_bad_extension_map(self):
        "Error creating a extension with a bad map"
        inmap = self.std_map()
        inmap.update({'pg_trgm': {'schema': 'public'}})
        with pytest.raises(KeyError):
            self.to_sql(inmap)

    def test_drop_extension(self):
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        "Drop an existing extension"
        sql = self.to_sql(self.std_map(), [CREATE_STMT], superuser=True)
        assert sql == ["DROP EXTENSION pg_trgm"]

    def test_create_extension_schema(self):
        "Create a extension in a given schema"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        inmap = self.std_map()
        inmap.update({'schema s1': {},
                      'extension pg_trgm': {'schema': 's1', 'version': '1.0'}})
        sql = self.to_sql(inmap)
        assert sql[0] == 'CREATE SCHEMA s1'
        assert fix_indent(sql[1]) == \
            "CREATE EXTENSION pg_trgm SCHEMA s1 VERSION '1.0'"

    def test_create_lang_extension(self):
        "Create a language extension and a function in that language"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        inmap = self.std_map()
        inmap.update({'extension plperl': {'schema': 'pg_catalog',
            'description': "PL/Perl procedural language"}})
        inmap['schema public'].update({'function f1()': {
            'language': 'plperl', 'returns': 'text',
            'source': "return \"dummy\";"}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == "CREATE EXTENSION plperl"
        # skip over COMMENT and SET statements
        assert fix_indent(sql[3]) == "CREATE FUNCTION f1() RETURNS text " \
            "LANGUAGE plperl AS $_$return \"dummy\";$_$"

    def test_comment_extension(self):
        "Change the comment for an existing extension"
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        inmap = self.std_map()
        inmap.update({'extension pg_trgm': {
            'schema': 'public', 'description': "Trigram extension"}})
        sql = self.to_sql(inmap, [CREATE_STMT], superuser=True)
        assert sql == ["COMMENT ON EXTENSION pg_trgm IS 'Trigram extension'"]

    def test_no_alter_owner_extension(self):
        """Do not alter the owner of an existing extension.

        ALTER EXTENSION extension_name OWNER is not a valid form.
        """
        if self.db.version < 90100:
            self.skipTest('Only available on PG 9.1')
        # create a new owner that is different from self.db.user
        new_owner = 'new_%s' % self.db.user
        inmap = self.std_map()
        inmap.update({'extension pg_trgm': {'schema': 'public',
                                            'owner': new_owner}})
        sql = self.to_sql(inmap, [CREATE_STMT], superuser=True)
        assert 'ALTER EXTENSION pg_trgm OWNER TO %s' % new_owner not in sql
