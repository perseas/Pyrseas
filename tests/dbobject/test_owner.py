# -*- coding: utf-8 -*-
"""Test object ownership

The majority of other tests exclude owner information.  These
explicitly request it.
"""

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

CREATE_TABLE = "CREATE TABLE sd.t1 (c1 integer, c2 text)"
SOURCE1 = "SELECT 'dummy'::text"
SOURCE2 = "SELECT $1 * $2"
CREATE_FUNC = "CREATE FUNCTION sd.f1() RETURNS text LANGUAGE sql IMMUTABLE " \
    "AS $_$%s$_$" % SOURCE1
CREATE_TYPE = "CREATE TYPE sd.t1 AS (x integer, y integer)"


class OwnerToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of object owner information"""

    def test_map_type(self):
        "Map a composite type"
        dbmap = self.to_map([CREATE_TYPE], no_owner=False)
        expmap = {'attributes': [{'x': {'type': 'integer'}},
                                 {'y': {'type': 'integer'}}],
                  'owner': self.db.user}
        assert dbmap['schema sd']['type t1'] == expmap

    def test_map_table(self):
        "Map a table"
        dbmap = self.to_map([CREATE_TABLE], no_owner=False)
        expmap = {'columns': [{'c1': {'type': 'integer'}},
                              {'c2': {'type': 'text'}}],
                  'owner': self.db.user}
        assert dbmap['schema sd']['table t1'] == expmap

    def test_map_function(self):
        "Map a function"
        dbmap = self.to_map([CREATE_FUNC], no_owner=False)
        expmap = {'language': 'sql', 'returns': 'text', 'owner': self.db.user,
                  'source': SOURCE1, 'volatility': 'immutable'}
        assert dbmap['schema sd']['function f1()'] == expmap


class OwnerToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation of owner object information"""

    def test_create_type(self):
        "Create a composite type"
        inmap = self.std_map()
        inmap['schema sd'].update({'type t1': {
            'attributes': [{'x': {'type': 'integer'}},
                           {'y': {'type': 'integer'}}],
            'owner': self.db.user}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == CREATE_TYPE
        assert sql[1] == "ALTER TYPE sd.t1 OWNER TO %s" % self.db.user

    def test_create_table(self):
        "Create a table"
        inmap = self.std_map()
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}}],
            'owner': self.db.user}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == CREATE_TABLE
        assert sql[1] == "ALTER TABLE sd.t1 OWNER TO %s" % self.db.user

    def test_create_function(self):
        "Create a function in a schema and a comment"
        inmap = self.std_map()
        inmap.update({'schema s1': {'function f1()': {
            'language': 'sql', 'returns': 'text', 'source': SOURCE1,
            'volatility': 'immutable', 'owner': self.db.user,
            'description': 'Test function'}}})
        sql = self.to_sql(inmap, ["CREATE SCHEMA s1"])
        # skip first two statements as those are tested elsewhere
        assert sql[2] == "ALTER FUNCTION s1.f1() OWNER TO %s" % self.db.user
        # to verify correct order of invocation of ownable and commentable
        assert sql[3] == "COMMENT ON FUNCTION s1.f1() IS 'Test function'"

    def test_create_function_default_args(self):
        "Create a function with default arguments"
        inmap = self.std_map()
        inmap['schema sd'].update({
            'function f1(integer, INOUT integer)': {
                'allargs': 'integer, INOUT integer DEFAULT 1',
                'language': 'sql', 'returns': 'integer', 'source': SOURCE2,
                'owner': self.db.user}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[1]) == \
            "CREATE FUNCTION sd.f1(integer, INOUT integer DEFAULT 1) " \
            "RETURNS integer LANGUAGE sql AS $_$%s$_$" % SOURCE2
        assert sql[2] == "ALTER FUNCTION sd.f1(integer, INOUT integer) " \
            "OWNER TO %s" % self.db.user

    def test_change_table_owner(self):
        "Change the owner of a table"
        inmap = self.std_map()
        inmap['schema sd'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}}],
            'owner': 'someuser'}})
        sql = self.to_sql(inmap, [CREATE_TABLE])
        assert sql[0] == "ALTER TABLE sd.t1 OWNER TO someuser"

    def test_change_table_owner_delim(self):
        "Change the owner of a table with delimited identifiers"
        inmap = self.std_map()
        inmap.update({'schema a-schema': {'table a-table': {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}}],
            'owner': 'someuser'}}})
        sql = self.to_sql(inmap, ["CREATE SCHEMA \"a-schema\"",
                                  "CREATE TABLE \"a-schema\".\"a-table\" ("
                                  "c1 integer, c2 text)"])
        assert sql[0] == "ALTER TABLE \"a-schema\".\"a-table\" OWNER TO " \
                          "someuser"
