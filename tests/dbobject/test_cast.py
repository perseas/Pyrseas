# -*- coding: utf-8 -*-
"""Test casts"""

import pytest

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

SOURCE = "SELECT CAST($1::int AS boolean)"
CREATE_FUNC = "CREATE FUNCTION int2_bool(smallint) RETURNS boolean " \
    "LANGUAGE sql IMMUTABLE AS $_$%s$_$" % SOURCE
CREATE_DOMAIN = "CREATE DOMAIN d1 AS integer"
CREATE_STMT1 = "CREATE CAST (smallint AS boolean) WITH FUNCTION " \
    "sd.int2_bool(smallint)"
CREATE_STMT3 = "CREATE CAST (d1 AS integer) WITH INOUT AS IMPLICIT"
DROP_STMT = "DROP CAST IF EXISTS (smallint AS boolean)"
COMMENT_STMT = "COMMENT ON CAST (smallint AS boolean) IS 'Test cast 1'"


class CastToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of existing casts"""

    def test_map_cast_function(self):
        "Map a cast with a function"
        dbmap = self.to_map([CREATE_FUNC, CREATE_STMT1], superuser=True)
        expmap = {'function': 'sd.int2_bool(smallint)', 'context': 'explicit',
                  'method': 'function'}
        assert dbmap['cast (smallint as boolean)'] == expmap

    def test_map_cast_inout(self):
        "Map a cast with INOUT"
        dbmap = self.to_map([CREATE_DOMAIN, CREATE_STMT3])
        expmap = {'context': 'implicit', 'method': 'inout',
                  'depends_on': ['domain d1']}
        assert dbmap['cast (sd.d1 as integer)'] == expmap

    def test_map_cast_comment(self):
        "Map a cast comment"
        dbmap = self.to_map([CREATE_FUNC, CREATE_STMT1, COMMENT_STMT],
                            superuser=True)
        assert dbmap['cast (smallint as boolean)']['description'] == \
            'Test cast 1'


class CastToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation from input casts"""

    def test_create_cast_function(self):
        "Create a cast with a function"
        stmts = [DROP_STMT, CREATE_FUNC]
        inmap = self.std_map()
        inmap.update({'cast (smallint as boolean)': {
            'function': 'sd.int2_bool(smallint)', 'context': 'explicit',
            'method': 'function'}})
        sql = self.to_sql(inmap, stmts)
        # NOTE(David Chang): This is a hack to get this test to work. We reordered all drops to happen before any other statements because in theory you shouldn't be depending on a function that used to exist for your cast. If you need it, you need to have it defined in your db.yaml to use it (and thus won't be dropped). However, this test is odd in how it runs and I don't think you can hit this case in real usage
        assert sql[0] == "DROP FUNCTION int2_bool(smallint)"
        assert fix_indent(sql[1]) == CREATE_STMT1

    def test_create_cast_inout(self):
        "Create a cast with INOUT"
        stmts = [CREATE_DOMAIN, "DROP CAST IF EXISTS (d1 AS integer)"]
        inmap = self.std_map()
        inmap.update({'cast (d1 as integer)': {
            'context': 'implicit', 'method': 'inout'}})
        inmap['schema sd'].update({'domain d1': {'type': 'integer'}})
        sql = self.to_sql(inmap, stmts)
        assert fix_indent(sql[0]) == CREATE_STMT3

    def test_create_cast_schema(self):
        "Create a cast using a type/domain in a non-default schema"
        stmts = ["CREATE SCHEMA s1", "CREATE DOMAIN s1.d1 AS integer",
                 "DROP CAST IF EXISTS (integer AS s1.d1)"]
        inmap = self.std_map()
        inmap.update({'cast (integer as s1.d1)': {
            'context': 'assignment', 'method': 'binary coercible'}})
        inmap.update({'schema s1': {'domain d1': {'type': 'integer'}}})
        sql = self.to_sql(inmap, stmts)
        assert fix_indent(sql[0]) == "CREATE CAST (integer AS s1.d1) " \
            "WITHOUT FUNCTION AS ASSIGNMENT"

    def test_bad_cast_map(self):
        "Error creating a cast with a bad map"
        inmap = self.std_map()
        inmap.update({'(smallint as boolean)': {
            'function': 'int2_bool(smallint)', 'context': 'explicit',
            'method': 'function'}})
        with pytest.raises(KeyError):
            self.to_sql(inmap)

    def test_drop_cast(self):
        "Drop an existing cast"
        stmts = [DROP_STMT, CREATE_FUNC, CREATE_STMT1]
        sql = self.to_sql(self.std_map(), stmts, superuser=True)
        assert sql[0] == "DROP CAST (smallint AS boolean)"

    def test_cast_with_comment(self):
        "Create a cast with a comment"
        inmap = self.std_map()
        inmap.update({'cast (smallint as boolean)': {
            'description': 'Test cast 1', 'function': 'sd.int2_bool(smallint)',
            'context': 'explicit', 'method': 'function'}})
        inmap['schema sd'].update({'function int2_bool(smallint)': {
            'returns': 'boolean', 'language': 'sql', 'immutable': True,
            'source': SOURCE}})
        sql = self.to_sql(inmap, [DROP_STMT])
        # sql[0:1] -> SET, CREATE FUNCTION
        assert fix_indent(sql[2]) == CREATE_STMT1
        assert sql[3] == COMMENT_STMT

    def test_comment_on_cast(self):
        "Create a comment for an existing cast"
        stmts = [DROP_STMT, CREATE_FUNC, CREATE_STMT1]
        inmap = self.std_map()
        inmap.update({'cast (smallint as boolean)': {
            'description': 'Test cast 1', 'function': 'int2_bool(smallint)',
            'context': 'explicit', 'method': 'function'}})
        inmap['schema sd'].update({'function int2_bool(smallint)': {
            'returns': 'boolean', 'language': 'sql', 'immutable': True,
            'source': SOURCE}})
        sql = self.to_sql(inmap, stmts, superuser=True)
        assert sql == [COMMENT_STMT]

    def test_drop_cast_comment(self):
        "Drop a comment on an existing cast"
        stmts = [DROP_STMT, CREATE_FUNC, CREATE_STMT1, COMMENT_STMT]
        inmap = self.std_map()
        inmap.update({'cast (smallint as boolean)': {
            'function': 'int2_bool(smallint)', 'context': 'explicit',
            'method': 'function'}})
        inmap['schema sd'].update({'function int2_bool(smallint)': {
            'returns': 'boolean', 'language': 'sql', 'immutable': True,
            'source': SOURCE}})
        assert self.to_sql(inmap, stmts, superuser=True) == \
            ["COMMENT ON CAST (smallint AS boolean) IS NULL"]

    def test_change_cast_comment(self):
        "Change existing comment on a cast"
        stmts = [DROP_STMT, CREATE_FUNC, CREATE_STMT1, COMMENT_STMT]
        inmap = self.std_map()
        inmap.update({'cast (smallint as boolean)': {
            'description': 'Changed cast 1', 'function': 'int2_bool(smallint)',
            'context': 'explicit', 'method': 'function'}})
        inmap['schema sd'].update({'function int2_bool(smallint)': {
            'returns': 'boolean', 'language': 'sql', 'immutable': True,
            'source': SOURCE}})
        assert self.to_sql(inmap, stmts, superuser=True) == \
            ["COMMENT ON CAST (smallint AS boolean) IS 'Changed cast 1'"]

    def test_cast_function_view_depends(self):
        "Cast that depends on a function that depends on a view.  See #86"
        stmts = ["CREATE TABLE t1 (id integer)"]
        inmap = self.std_map()
        inmap.update({'cast (sd.v1 as sd.t1)': {
            'context': 'explicit', 'function': 'sd.v1_to_t1(sd.v1)',
            'method': 'function'}})
        inmap['schema sd'].update({
            'function v1_to_t1(sd.v1)': {
                'returns': 'sd.t1', 'language': 'plpgsql',
                'source': "\nDECLARE o sd.t1;\nBEGIN o:= ROW($1.id)::t1;\n"
                "RETURN o;\nEND"},
            'table t1': {'columns': [{'id': {'type': 'integer'}}]},
            'view v1': {'definition': " SELECT t1.id\n    FROM sd.t1;",
                        'depends_on': ['table t1']}})
        sql = self.to_sql(inmap, stmts)
        assert len(sql) == 3
        assert fix_indent(sql[0]) == \
            "CREATE VIEW sd.v1 AS SELECT t1.id FROM sd.t1"
        assert fix_indent(sql[1]) == "CREATE FUNCTION sd.v1_to_t1(sd.v1) " \
            "RETURNS sd.t1 LANGUAGE plpgsql AS $_$\nDECLARE o sd.t1;\n" \
            "BEGIN o:= ROW($1.id)::t1;\nRETURN o;\nEND$_$"
        assert fix_indent(sql[2]) == "CREATE CAST (sd.v1 AS sd.t1) WITH " \
            "FUNCTION sd.v1_to_t1(sd.v1)"
