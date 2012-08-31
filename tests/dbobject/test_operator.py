# -*- coding: utf-8 -*-
"""Test operators"""

import unittest

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

CREATE_STMT = "CREATE OPERATOR + (PROCEDURE = textcat, LEFTARG = text, " \
    "RIGHTARG = text)"
DROP_STMT = "DROP OPERATOR IF EXISTS +(text, text)"
COMMENT_STMT = "COMMENT ON OPERATOR +(text, text) IS 'Test operator +'"


class OperatorToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of existing operators"""

    def test_map_operator(self):
        "Map a simple operator"
        dbmap = self.to_map([CREATE_STMT])
        expmap = {'procedure': 'textcat'}
        self.assertEqual(dbmap['schema public']['operator +(text, text)'],
                         expmap)

    def test_map_operator_rightarg(self):
        "Map a unitary operator with a right argument"
        stmts = ["CREATE OPERATOR + (PROCEDURE = upper, RIGHTARG = text)"]
        dbmap = self.to_map(stmts)
        if self.db.version < 90200:
            expmap = {'procedure': 'upper'}
        else:
            expmap = {'procedure': 'pg_catalog.upper'}
        self.assertEqual(dbmap['schema public']['operator +(NONE, text)'],
                         expmap)

    def test_map_operator_commutator(self):
        "Map an operator with a commutator"
        stmts = ["CREATE OPERATOR && (PROCEDURE = int4pl, LEFTARG = integer, "
                 "RIGHTARG = integer, COMMUTATOR = OPERATOR(public.&&))"]
        dbmap = self.to_map(stmts)
        expmap = {'procedure': 'int4pl', 'commutator': 'public.&&'}
        self.assertEqual(dbmap['schema public']
                         ['operator &&(integer, integer)'], expmap)

    def test_map_operator_hash(self):
        "Map an operator with HASHES clause"
        stmts = ["CREATE OPERATOR + (PROCEDURE = texteq, LEFTARG = text, "
                 "RIGHTARG = text, HASHES)"]
        dbmap = self.to_map(stmts)
        expmap = {'procedure': 'texteq', 'hashes': True}
        self.assertEqual(dbmap['schema public']['operator +(text, text)'],
                         expmap)

    def test_map_operator_comment(self):
        "Map a operator comment"
        dbmap = self.to_map([CREATE_STMT, COMMENT_STMT])
        self.assertEqual(dbmap['schema public']
                         ['operator +(text, text)']['description'],
                         'Test operator +')


class OperatorToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation from input operators"""

    def test_create_operator(self):
        "Create a simple operator"
        inmap = self.std_map()
        inmap['schema public'].update({'operator +(text, text)': {
                    'procedure': 'textcat'}})
        sql = self.to_sql(inmap)
        self.assertEqual(fix_indent(sql[0]), CREATE_STMT)

    def test_create_operator_rightarg(self):
        "Create a unitary operator with a right argument"
        inmap = self.std_map()
        inmap['schema public'].update({'operator +(NONE, text)': {
                    'procedure': 'upper'}})
        sql = self.to_sql(inmap)
        self.assertEqual(fix_indent(sql[0]), "CREATE OPERATOR + ("
                         "PROCEDURE = upper, RIGHTARG = text)")

    def test_create_operator_commutator(self):
        "Create an operator with a commutator"
        inmap = self.std_map()
        inmap['schema public'].update({'operator &&(integer, integer)': {
                    'procedure': 'int4pl', 'commutator': 'public.&&'}})
        sql = self.to_sql(inmap)
        self.assertEqual(fix_indent(sql[0]),
                         "CREATE OPERATOR && (PROCEDURE = int4pl, LEFTARG = "
                         "integer, RIGHTARG = integer, COMMUTATOR = "
                         "OPERATOR(public.&&))")

    def test_create_operator_in_schema(self):
        "Create a operator within a non-public schema"
        inmap = self.std_map()
        inmap.update({'schema s1': {'operator +(text, text)': {
                    'procedure': 'textcat'}}})
        sql = self.to_sql(inmap, ["CREATE SCHEMA s1"])
        self.assertEqual(fix_indent(sql[0]), "CREATE OPERATOR s1.+ "
                         "(PROCEDURE = textcat, LEFTARG = text, "
                         "RIGHTARG = text)")

    def test_drop_operator(self):
        "Drop an existing operator"
        sql = self.to_sql(self.std_map(), [CREATE_STMT])
        self.assertEqual(sql, ["DROP OPERATOR +(text, text)"])

    def test_operator_with_comment(self):
        "Create a operator with a comment"
        inmap = self.std_map()
        inmap['schema public'].update({
                'operator +(text, text)': {
                    'description': 'Test operator +',
                    'procedure': 'textcat'}})
        sql = self.to_sql(inmap)
        self.assertEqual(fix_indent(sql[0]), CREATE_STMT)
        self.assertEqual(sql[1], COMMENT_STMT)

    def test_comment_on_operator(self):
        "Create a comment for an existing operator"
        inmap = self.std_map()
        inmap['schema public'].update({
                'operator +(text, text)': {
                    'description': 'Test operator +',
                    'procedure': 'textcat'}})
        sql = self.to_sql(inmap, [CREATE_STMT])
        self.assertEqual(sql, [COMMENT_STMT])

    def test_drop_operator_comment(self):
        "Drop a comment on an existing operator"
        stmts = [CREATE_STMT, COMMENT_STMT]
        inmap = self.std_map()
        inmap['schema public'].update({
                'operator +(text, text)': {
                    'language': 'sql', 'returns': 'integer',
                    'procedure': 'textcat'}})
        sql = self.to_sql(inmap, stmts)
        self.assertEqual(sql, ["COMMENT ON OPERATOR +(text, text) IS NULL"])

    def test_change_operator_comment(self):
        "Change existing comment on a operator"
        stmts = [CREATE_STMT, COMMENT_STMT]
        inmap = self.std_map()
        inmap['schema public'].update({
                'operator +(text, text)': {
                    'description': 'Changed operator +',
                    'procedure': 'textcat'}})
        sql = self.to_sql(inmap, stmts)
        self.assertEqual(sql, [
                "COMMENT ON OPERATOR +(text, text) IS "
                "'Changed operator +'"])


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(OperatorToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            OperatorToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
