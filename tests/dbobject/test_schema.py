# -*- coding: utf-8 -*-
"""Test schemas"""

import pytest

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase

CREATE_STMT = "CREATE SCHEMA s1"
COMMENT_STMT = "COMMENT ON SCHEMA s1 IS 'Test schema s1'"


class SchemaToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of created schemas"""

    def test_map_schema(self):
        "Map a created schema"
        dbmap = self.to_map([CREATE_STMT])
        assert dbmap['schema s1'] == {}

    def test_map_schema_comment(self):
        "Map a schema comment"
        dbmap = self.to_map([CREATE_STMT, COMMENT_STMT])
        assert dbmap['schema s1'] == {'description': 'Test schema s1'}

    def test_map_select_schema(self):
        "Map a single schema when three schemas exist"
        stmts = [CREATE_STMT, "CREATE SCHEMA s2", "CREATE SCHEMA s3"]
        dbmap = self.to_map(stmts, schemas=['s2'])
        assert 'schema s1' not in dbmap
        assert dbmap['schema s2'] == {}
        assert 'schema s3' not in dbmap


class SchemaToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation from input schemas"""

    def base_schmap(self):
        return {'schema s1': {'description': 'Test schema s1'}}

    def test_create_schema(self):
        "Create a new schema"
        inmap = self.std_map()
        inmap.update({'schema s1': {}})
        sql = self.to_sql(inmap)
        assert sql == [CREATE_STMT]

    def test_bad_schema_map(self):
        "Error creating a schema with a bad map"
        with pytest.raises(KeyError):
            self.to_sql({'s1': {}})

    def test_drop_schema(self):
        "Drop an existing schema"
        sql = self.to_sql(self.std_map(), [CREATE_STMT])
        assert sql == ["DROP SCHEMA s1"]

    def test_rename_schema(self):
        "Rename an existing schema"
        inmap = self.std_map()
        inmap.update({'schema s2': {'oldname': 's1'}})
        sql = self.to_sql(inmap, [CREATE_STMT])
        assert sql == ["ALTER SCHEMA s1 RENAME TO s2"]

    def test_bad_rename_schema(self):
        "Error renaming a non-existing schema"
        inmap = self.std_map()
        inmap.update({'schema s2': {'oldname': 's3'}})
        with pytest.raises(KeyError):
            self.to_sql(inmap, [CREATE_STMT])

    def test_schema_with_comment(self):
        "Create a schema with a comment"
        inmap = self.std_map()
        inmap.update(self.base_schmap())
        sql = self.to_sql(inmap)
        assert sql == [CREATE_STMT, COMMENT_STMT]

    def test_comment_on_schema(self):
        "Create a comment for an existing schema"
        inmap = self.std_map()
        inmap.update(self.base_schmap())
        sql = self.to_sql(inmap, [CREATE_STMT])
        assert sql == [COMMENT_STMT]

    def test_drop_schema_comment(self):
        "Drop a comment on an existing schema"
        inmap = self.std_map()
        inmap.update({'schema s1': {}})
        stmts = [CREATE_STMT, COMMENT_STMT]
        sql = self.to_sql(inmap, stmts)
        assert sql == ["COMMENT ON SCHEMA s1 IS NULL"]

    def test_change_schema_comment(self):
        "Change existing comment on a schema"
        inmap = self.std_map()
        inmap.update({'schema s1': {'description': 'Changed schema s1'}})
        stmts = [CREATE_STMT, COMMENT_STMT]
        sql = self.to_sql(inmap, stmts)
        assert sql == ["COMMENT ON SCHEMA s1 IS 'Changed schema s1'"]


class SchemaUndoSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation to revert schemas"""

    def base_schmap(self):
        return {'schema s1': {'description': 'Test schema s1'}}

    def test_undo_create_schema(self):
        "Revert a schema creation"
        inmap = self.std_map()
        inmap.update({'schema s1': {}})
        sql = self.to_sql(inmap, revert=True)
        assert sql == ["DROP SCHEMA s1"]

    def test_undo_drop_schema(self):
        "Revert dropping a schema"
        sql = self.to_sql(self.std_map(), [CREATE_STMT], revert=True)
        assert sql[0] == CREATE_STMT

    def test_undo_comment_on_schema(self):
        "Revert creating comment on a schema"
        inmap = self.std_map()
        inmap.update(self.base_schmap())
        sql = self.to_sql(inmap, [CREATE_STMT], revert=True)
        assert sql == ["COMMENT ON SCHEMA s1 IS NULL"]

    def test_undo_drop_schema_comment(self):
        "Revert dropping comment on a schema"
        inmap = self.std_map()
        inmap.update({'schema s1': {}})
        stmts = [CREATE_STMT, COMMENT_STMT]
        sql = self.to_sql(inmap, stmts, revert=True)
        assert sql == [COMMENT_STMT]
