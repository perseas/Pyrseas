# -*- coding: utf-8 -*-
"""Test extensions"""

import pytest

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

CREATE_STMT = "CREATE EXTENSION pg_trgm"
TRGM_COMMENT = "text similarity measurement and index searching based on " \
    "trigrams"
PLR_DESCR = "load R interpreter and execute R script from within a database"


class ExtensionToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of existing extensions"""

    superuser = True
    def base_version(self):
        if self.db.version < 110000:
            return '1.3'
        elif self.db.version < 120000:
            return '1.4'
        elif self.db.version < 150000:
            return  '1.5'
        return '1.6'

    def test_map_extension(self):
        "Map an existing extension"
        VERS = self.base_version()
        dbmap = self.to_map([CREATE_STMT])
        assert dbmap['extension pg_trgm'] == {
            'schema': 'sd', 'version': VERS, 'description': TRGM_COMMENT}

    def test_map_no_depends(self):
        "Ensure no dependencies are included when mapping an extension"
        dbmap = self.to_map([CREATE_STMT])
        assert 'type gtrgm' not in dbmap['schema sd']
        assert 'operator %(text, text)' not in dbmap['schema sd']
        assert 'function show_trgm(text)' not in dbmap['schema sd']

    def test_map_lang_extension(self):
        "Map a procedural language as an extension"
        dbmap = self.to_map(["CREATE EXTENSION plperl"])
        assert dbmap['extension plperl'] == {
            'schema': 'pg_catalog', 'version': '1.0',
            'description': "PL/Perl procedural language"}
        assert 'language plperl' not in dbmap

    def test_map_extern_lang_extension(self):
        "Map an externally maintained procedural language"
        if self.db.version < 150000:
            self.skipTest('Only available since PG 15')
        dbmap = self.to_map(["CREATE EXTENSION plr"])
        assert dbmap['extension plr'] == {
            'schema': 'sd', 'version': '8.4.5', 'description': PLR_DESCR}
        assert dbmap['language plr'] == {'trusted': False}
        # Ensure we don't map core-maintained language
        assert 'language plpgsql' not in dbmap

    def test_map_extension_schema(self):
        "Map an existing extension"
        VERS = self.base_version()
        dbmap = self.to_map(["CREATE SCHEMA s1", CREATE_STMT + " SCHEMA s1"])
        assert dbmap['extension pg_trgm'] == {
            'schema': 's1', 'version': VERS, 'description': TRGM_COMMENT}

    def test_map_extension_plpython3u(self):
        "Test a function created with extension other than plpgsql/plperl"
        # See issue #103
        dbmap = self.to_map(["CREATE EXTENSION plpython3u",
                             "CREATE FUNCTION test() RETURNS int AS "
                             "'return 1' LANGUAGE plpython3u"])
        assert 'extension plpython3u' in dbmap


class ExtensionToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation for input extensions"""

    def test_create_extension_simple(self):
        "Create a extension that didn't exist"
        inmap = self.std_map()
        inmap.update({'extension pg_trgm': {'schema': 'sd'}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == CREATE_STMT + " SCHEMA sd"

    def test_bad_extension_map(self):
        "Error creating a extension with a bad map"
        inmap = self.std_map()
        inmap.update({'pg_trgm': {'schema': 'sd'}})
        with pytest.raises(KeyError):
            self.to_sql(inmap)

    def test_drop_extension(self):
        "Drop an existing extension"
        sql = self.to_sql(self.std_map(), [CREATE_STMT], superuser=True)
        assert sql == ["DROP EXTENSION pg_trgm"]

    def test_create_extension_schema(self):
        "Create a extension in a given schema"
        inmap = self.std_map()
        inmap.update({'schema s1': {},
                      'extension pg_trgm': {'schema': 's1', 'version': '1.0'}})
        sql = self.to_sql(inmap)
        assert sql[0] == 'CREATE SCHEMA s1'
        assert fix_indent(sql[1]) == \
            "CREATE EXTENSION pg_trgm SCHEMA s1 VERSION '1.0'"

    def test_create_lang_extension(self):
        "Create a language extension and a function in that language"
        inmap = self.std_map()
        inmap.update({'extension plperl': {'schema': 'pg_catalog',
                                           'description':
                                           "PL/Perl procedural language"}})
        inmap['schema sd'].update({'function f1()': {
            'language': 'plperl', 'returns': 'text',
            'source': "return \"dummy\";"}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == "CREATE EXTENSION plperl"
        # skip over COMMENT statement
        assert fix_indent(sql[2]) == "CREATE FUNCTION sd.f1() RETURNS text " \
            "LANGUAGE plperl AS $_$return \"dummy\";$_$"

    def test_create_extern_lang_extension(self):
        "Create an externally maintained language together with a function"
        inmap = self.std_map()
        inmap.update({'extension plr': {'schema': 'sd',
                                        'description': PLR_DESCR}})
        inmap.update({'language plr': { 'trusted': 'false'}})
        inmap['schema sd'].update({'function f1()': {
            'language': 'plr', 'returns': 'text',
            'source': "return \"dummy\";"}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == "CREATE EXTENSION plr SCHEMA sd"
        # skip over COMMENT statement
        assert fix_indent(sql[2]) == "CREATE FUNCTION sd.f1() RETURNS text " \
            "LANGUAGE plr AS $_$return \"dummy\";$_$"

    def test_comment_extension(self):
        "Change the comment for an existing extension"
        inmap = self.std_map()
        inmap.update({'extension pg_trgm': {
            'schema': 'sd', 'description': "Trigram extension"}})
        sql = self.to_sql(inmap, [CREATE_STMT], superuser=True)
        assert sql == ["COMMENT ON EXTENSION pg_trgm IS 'Trigram extension'"]

    def test_no_alter_owner_extension(self):
        """Do not alter the owner of an existing extension.

        ALTER EXTENSION extension_name OWNER is not a valid form.
        """
        # create a new owner that is different from self.db.user
        new_owner = 'new_%s' % self.db.user
        inmap = self.std_map()
        inmap.update({'extension pg_trgm': {'schema': 'sd',
                                            'owner': new_owner}})
        sql = self.to_sql(inmap, [CREATE_STMT], superuser=True)
        assert 'ALTER EXTENSION pg_trgm OWNER TO %s' % new_owner not in sql
