# -*- coding: utf-8 -*-
"""Test operator families"""

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

CREATE_STMT = "CREATE OPERATOR FAMILY sd.of1 USING btree"
COMMENT_STMT = "COMMENT ON OPERATOR FAMILY sd.of1 USING btree IS " \
    "'Test operator family of1'"


class OperatorFamilyToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of existing operators"""

    superuser = True

    def test_map_operfam(self):
        "Map an operator family"
        dbmap = self.to_map([CREATE_STMT])
        assert dbmap['schema sd']['operator family of1 using btree'] == {}

    def test_map_operfam_comment(self):
        "Map an operator family comment"
        dbmap = self.to_map([CREATE_STMT, COMMENT_STMT])
        assert dbmap['schema sd']['operator family of1 using btree'][
            'description'] == 'Test operator family of1'


class OperatorFamilyToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation from input operators"""

    def test_create_operfam(self):
        "Create an operator family"
        inmap = self.std_map()
        inmap['schema sd'].update({'operator family of1 using btree': {}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == CREATE_STMT

    def test_create_operfam_in_schema(self):
        "Create an operator family within a non-default schema"
        inmap = self.std_map()
        inmap.update({'schema s1': {'operator family of1 using btree': {}}})
        sql = self.to_sql(inmap, ["CREATE SCHEMA s1"])
        assert fix_indent(sql[0]) == \
            "CREATE OPERATOR FAMILY s1.of1 USING btree"

    def test_drop_operfam(self):
        "Drop an existing operator family"
        sql = self.to_sql(self.std_map(), [CREATE_STMT], superuser=True)
        assert sql == ["DROP OPERATOR FAMILY sd.of1 USING btree"]

    def test_operfam_with_comment(self):
        "Create an operator family with a comment"
        inmap = self.std_map()
        inmap['schema sd'].update({'operator family of1 using btree': {
            'description': 'Test operator family of1'}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == CREATE_STMT
        assert sql[1] == COMMENT_STMT

    def test_comment_on_operfam(self):
        "Create a comment for an existing operator family"
        inmap = self.std_map()
        inmap['schema sd'].update({'operator family of1 using btree': {
            'description': 'Test operator family of1'}})
        sql = self.to_sql(inmap, [CREATE_STMT], superuser=True)
        assert sql == [COMMENT_STMT]

    def test_drop_operfam_comment(self):
        "Drop a comment on an existing operator family"
        stmts = [CREATE_STMT, COMMENT_STMT]
        inmap = self.std_map()
        inmap['schema sd'].update({'operator family of1 using btree': {}})
        sql = self.to_sql(inmap, stmts, superuser=True)
        assert sql == ["COMMENT ON OPERATOR FAMILY sd.of1 USING btree IS NULL"]

    def test_change_operfam_comment(self):
        "Change existing comment on a operator"
        stmts = [CREATE_STMT, COMMENT_STMT]
        inmap = self.std_map()
        inmap['schema sd'].update({'operator family of1 using btree': {
            'description': 'Changed operator family of1'}})
        sql = self.to_sql(inmap, stmts, superuser=True)
        assert sql == ["COMMENT ON OPERATOR FAMILY sd.of1 USING btree IS "
                       "'Changed operator family of1'"]
