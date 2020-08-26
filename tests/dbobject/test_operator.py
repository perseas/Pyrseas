# -*- coding: utf-8 -*-
"""Test operators"""

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

CREATE_STMT = "CREATE OPERATOR sd.+ (PROCEDURE = textcat, LEFTARG = text, " \
    "RIGHTARG = text)"
COMMENT_STMT = "COMMENT ON OPERATOR sd.+(text, text) IS 'Test operator +'"


class OperatorToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of existing operators"""

    def test_map_operator1(self):
        "Map a simple operator"
        dbmap = self.to_map([CREATE_STMT])
        expmap = {'procedure': 'textcat'}
        assert dbmap['schema sd']['operator +(text, text)'] == expmap

    def test_map_operator_rightarg(self):
        "Map a unitary operator with a right argument"
        stmts = ["CREATE OPERATOR + (PROCEDURE = upper, RIGHTARG = text)"]
        dbmap = self.to_map(stmts)
        if self.db.version < 90200:
            expmap = {'procedure': 'upper'}
        else:
            expmap = {'procedure': 'pg_catalog.upper'}
        assert dbmap['schema sd']['operator +(NONE, text)'] == expmap

    def test_map_operator_commutator(self):
        "Map an operator with a commutator"
        stmts = ["CREATE OPERATOR && (PROCEDURE = int4pl, LEFTARG = integer, "
                 "RIGHTARG = integer, COMMUTATOR = OPERATOR(sd.&&))"]
        dbmap = self.to_map(stmts)
        assert dbmap['schema sd']['operator &&(integer, integer)'] == \
            {'procedure': 'int4pl', 'commutator': 'sd.&&'}

    def test_map_operator_hash(self):
        "Map an operator with HASHES clause"
        stmts = ["CREATE OPERATOR + (PROCEDURE = texteq, LEFTARG = text, "
                 "RIGHTARG = text, HASHES)"]
        dbmap = self.to_map(stmts)
        expmap = {'procedure': 'texteq', 'hashes': True}
        assert dbmap['schema sd']['operator +(text, text)'] == expmap

    def test_map_operator_comment(self):
        "Map a operator comment"
        dbmap = self.to_map([CREATE_STMT, COMMENT_STMT])
        assert dbmap['schema sd']['operator +(text, text)'][
            'description'] == 'Test operator +'


class OperatorToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation from input operators"""

    def test_create_operator1(self):
        "Create a simple operator"
        inmap = self.std_map()
        inmap['schema sd'].update({'operator +(text, text)': {
            'procedure': 'textcat'}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == CREATE_STMT

    def test_create_operator_rightarg(self):
        "Create a unitary operator with a right argument"
        inmap = self.std_map()
        inmap['schema sd'].update({'operator +(NONE, text)': {
            'procedure': 'upper'}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == "CREATE OPERATOR sd.+ (" \
            "PROCEDURE = upper, RIGHTARG = text)"

    def test_create_operator_commutator(self):
        "Create an operator with a commutator"
        inmap = self.std_map()
        inmap['schema sd'].update({'operator &&(integer, integer)': {
            'procedure': 'int4pl', 'commutator': 'sd.&&'}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == "CREATE OPERATOR sd.&& (" \
            "PROCEDURE = int4pl, LEFTARG = integer, RIGHTARG = integer, " \
            "COMMUTATOR = OPERATOR(sd.&&))"

    def test_create_operator_in_schema(self):
        "Create a operator within a non-default schema"
        inmap = self.std_map()
        inmap.update({'schema s1': {'operator +(text, text)': {
            'procedure': 'textcat'}}})
        sql = self.to_sql(inmap, ["CREATE SCHEMA s1"])
        assert fix_indent(sql[0]) == "CREATE OPERATOR s1.+ " \
            "(PROCEDURE = textcat, LEFTARG = text, RIGHTARG = text)"

    def test_drop_operator(self):
        "Drop an existing operator"
        sql = self.to_sql(self.std_map(), [CREATE_STMT])
        assert sql == ["DROP OPERATOR sd.+(text, text)"]

    def test_operator_with_comment(self):
        "Create a operator with a comment"
        inmap = self.std_map()
        inmap['schema sd'].update({
            'operator +(text, text)': {'description': 'Test operator +',
                                       'procedure': 'textcat'}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == CREATE_STMT
        assert sql[1] == COMMENT_STMT

    def test_comment_on_operator(self):
        "Create a comment for an existing operator"
        inmap = self.std_map()
        inmap['schema sd'].update({
            'operator +(text, text)': {'description': 'Test operator +',
                                       'procedure': 'textcat'}})
        sql = self.to_sql(inmap, [CREATE_STMT])
        assert sql == [COMMENT_STMT]

    def test_drop_operator_comment(self):
        "Drop a comment on an existing operator"
        stmts = [CREATE_STMT, COMMENT_STMT]
        inmap = self.std_map()
        inmap['schema sd'].update({
            'operator +(text, text)': {'returns': 'integer',
                                       'procedure': 'textcat'}})
        sql = self.to_sql(inmap, stmts)
        assert sql == ["COMMENT ON OPERATOR sd.+(text, text) IS NULL"]

    def test_change_operator_comment(self):
        "Change existing comment on a operator"
        stmts = [CREATE_STMT, COMMENT_STMT]
        inmap = self.std_map()
        inmap['schema sd'].update({
            'operator +(text, text)': {'description': 'Changed operator +',
                                       'procedure': 'textcat'}})
        sql = self.to_sql(inmap, stmts)
        assert sql == ["COMMENT ON OPERATOR sd.+(text, text) IS "
                       "'Changed operator +'"]
