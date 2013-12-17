# -*- coding: utf-8 -*-
"""Test sequences"""

import pytest

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

CREATE_STMT = "CREATE SEQUENCE seq1"
CREATE_STMT_FULL = "CREATE SEQUENCE seq1 START WITH 1 INCREMENT BY 1 " \
    "NO MAXVALUE NO MINVALUE CACHE 1"
COMMENT_STMT = "COMMENT ON SEQUENCE seq1 IS 'Test sequence seq1'"


class SequenceToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of created sequences"""

    def test_map_sequence(self):
        "Map a created sequence"
        dbmap = self.to_map([CREATE_STMT])
        expmap = {'start_value': 1, 'increment_by': 1, 'max_value': None,
                  'min_value': None, 'cache_value': 1}
        assert dbmap['schema public']['sequence seq1'] == expmap

    def test_map_sequence_comment(self):
        "Map a sequence with a comment"
        dbmap = self.to_map([CREATE_STMT, COMMENT_STMT])
        assert dbmap['schema public']['sequence seq1']['description'] == \
            'Test sequence seq1'


class SequenceToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation from input sequences"""

    def test_create_sequence(self):
        "Create a sequence"
        inmap = self.std_map()
        inmap['schema public'].update({'sequence seq1': {
            'start_value': 1, 'increment_by': 1, 'max_value': None,
            'min_value': None, 'cache_value': 1}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == CREATE_STMT_FULL

    def test_create_sequence_in_schema(self):
        "Create a sequence within a non-public schema"
        inmap = self.std_map()
        inmap.update({'schema s1': {'sequence seq1': {
            'start_value': 1, 'increment_by': 1, 'max_value': None,
            'min_value': None, 'cache_value': 1}}})
        sql = self.to_sql(inmap, ["CREATE SCHEMA s1"])
        assert fix_indent(sql[0]) == "CREATE SEQUENCE s1.seq1 START WITH 1 " \
            "INCREMENT BY 1 NO MAXVALUE NO MINVALUE CACHE 1"

    def test_bad_sequence_map(self):
        "Error creating a sequence with a bad map"
        inmap = self.std_map()
        inmap['schema public'].update({'seq1': {
            'start_value': 1, 'increment_by': 1, 'max_value': None,
            'min_value': None, 'cache_value': 1}})
        with pytest.raises(KeyError):
            self.to_sql(inmap)

    def test_drop_sequence(self):
        "Drop an existing sequence"
        sql = self.to_sql(self.std_map(), [CREATE_STMT])
        assert sql == ["DROP SEQUENCE seq1"]

    def test_rename_sequence(self):
        "Rename an existing sequence"
        inmap = self.std_map()
        inmap['schema public'].update({'sequence seq2': {
            'oldname': 'seq1', 'start_value': 1, 'increment_by': 1,
            'max_value': None, 'min_value': None, 'cache_value': 1}})
        sql = self.to_sql(inmap, [CREATE_STMT])
        assert sql == ["ALTER SEQUENCE seq1 RENAME TO seq2"]

    def test_bad_rename_sequence(self):
        "Error renaming a non-existing sequence"
        inmap = self.std_map()
        inmap['schema public'].update({'sequence seq2': {
            'oldname': 'seq3', 'start_value': 1, 'increment_by': 1,
            'max_value': None, 'min_value': None, 'cache_value': 1}})
        with pytest.raises(KeyError):
            self.to_sql(inmap, [CREATE_STMT])

    def test_change_sequence(self):
        "Change sequence attributes"
        inmap = self.std_map()
        inmap['schema public'].update({'sequence seq1': {
            'start_value': 5, 'increment_by': 10, 'max_value': None,
            'min_value': None, 'cache_value': 30}})
        sql = self.to_sql(inmap, [CREATE_STMT])
        assert fix_indent(sql[0]) == "ALTER SEQUENCE seq1 START WITH 5 " \
            "INCREMENT BY 10 CACHE 30"

    def test_sequence_with_comment(self):
        "Create a sequence with a comment"
        inmap = self.std_map()
        inmap['schema public'].update({'sequence seq1': {
            'start_value': 1, 'increment_by': 1, 'max_value': None,
            'min_value': None, 'cache_value': 1,
            'description': "Test sequence seq1"}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == CREATE_STMT_FULL
        assert sql[1] == COMMENT_STMT

    def test_comment_on_sequence(self):
        "Create a comment for an existing sequence"
        inmap = self.std_map()
        inmap['schema public'].update({'sequence seq1': {
            'start_value': 1, 'increment_by': 1, 'max_value': None,
            'min_value': None, 'cache_value': 1,
            'description': "Test sequence seq1"}})
        sql = self.to_sql(inmap, [CREATE_STMT])
        assert sql == [COMMENT_STMT]

    def test_drop_sequence_comment(self):
        "Drop the comment on an existing sequence"
        stmts = [CREATE_STMT, COMMENT_STMT]
        inmap = self.std_map()
        inmap['schema public'].update({'sequence seq1': {
            'start_value': 1, 'increment_by': 1, 'max_value': None,
            'min_value': None, 'cache_value': 1}})
        sql = self.to_sql(inmap, stmts)
        assert sql == ["COMMENT ON SEQUENCE seq1 IS NULL"]

    def test_change_sequence_comment(self):
        "Change existing comment on a sequence"
        stmts = [CREATE_STMT, COMMENT_STMT]
        inmap = self.std_map()
        inmap['schema public'].update({'sequence seq1': {
            'start_value': 1, 'increment_by': 1, 'max_value': None,
            'min_value': None, 'cache_value': 1,
            'description': "Changed sequence seq1"}})
        sql = self.to_sql(inmap, stmts)
        assert sql, ["COMMENT ON SEQUENCE seq1 IS 'Changed sequence seq1'"]


class SequenceUndoSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation to revert sequences"""

    def test_undo_create_sequence(self):
        "Revert a sequence creation"
        inmap = self.std_map()
        inmap['schema public'].update({'sequence seq1': {
            'start_value': 1, 'increment_by': 1, 'max_value': None,
            'min_value': None, 'cache_value': 1}})
        sql = self.to_sql(inmap, revert=True)
        assert sql == ["DROP SEQUENCE seq1"]

    def test_undo_create_sequence_in_schema(self):
        "Revert creating a sequence in a non-public schema"
        inmap = self.std_map()
        inmap.update({'schema s1': {'sequence seq1': {
            'start_value': 1, 'increment_by': 1, 'max_value': None,
            'min_value': None, 'cache_value': 1}}})
        sql = self.to_sql(inmap, ["CREATE SCHEMA s1"], revert=True)
        assert sql == ["DROP SEQUENCE s1.seq1"]

    def test_undo_drop_sequence(self):
        "Revert dropping a sequence"
        sql = self.to_sql(self.std_map(), [CREATE_STMT], revert=True)
        assert fix_indent(sql[0]) == CREATE_STMT_FULL

    def test_undo_change_sequence(self):
        "Revert changing sequence attributes"
        inmap = self.std_map()
        inmap['schema public'].update({'sequence seq1': {
            'start_value': 5, 'increment_by': 10, 'max_value': None,
            'min_value': None, 'cache_value': 30}})
        sql = self.to_sql(inmap, [CREATE_STMT], revert=True)
        assert fix_indent(sql[0]) == "ALTER SEQUENCE seq1 START WITH 1 " \
            "INCREMENT BY 1 NO MAXVALUE NO MINVALUE CACHE 1"
