# -*- coding: utf-8 -*-
"""Test operators"""

import unittest

from pyrseas.testutils import PyrseasTestCase, fix_indent

CREATE_STMT = "CREATE OPERATOR + (PROCEDURE = textcat, LEFTARG = text, " \
    "RIGHTARG = text)"
DROP_STMT = "DROP OPERATOR IF EXISTS +(text, text)"
COMMENT_STMT = "COMMENT ON OPERATOR +(text, text) IS 'Test operator +'"


class OperatorToMapTestCase(PyrseasTestCase):
    """Test mapping of existing operators"""

    def test_map_operator(self):
        "Map a simple operator"
        expmap = {'procedure': 'textcat'}
        dbmap = self.db.execute_and_map(CREATE_STMT)
        self.assertEqual(dbmap['schema public']['operator +(text, text)'],
                         expmap)

    def test_map_operator_rightarg(self):
        "Map a unitary operator with a right argument"
        expmap = {'procedure': 'upper'}
        dbmap = self.db.execute_and_map("CREATE OPERATOR + ("
                                        "PROCEDURE = upper, RIGHTARG = text)")
        self.assertEqual(dbmap['schema public']['operator +(NONE, text)'],
                         expmap)

    def test_map_operator_commutator(self):
        "Map an operator with a commutator"
        expmap = {'procedure': 'int4pl', 'commutator': 'public.&&'}
        dbmap = self.db.execute_and_map(
            "CREATE OPERATOR && (PROCEDURE = int4pl, LEFTARG = integer, "
            "RIGHTARG = integer, COMMUTATOR = OPERATOR(public.&&))")
        self.assertEqual(dbmap['schema public']
                         ['operator &&(integer, integer)'], expmap)

    def test_map_operator_hash(self):
        "Map an operator with HASHES clause"
        expmap = {'procedure': 'texteq', 'hashes': True}
        dbmap = self.db.execute_and_map(
            "CREATE OPERATOR + (PROCEDURE = texteq, LEFTARG = text, "
            "RIGHTARG = text, HASHES)")
        self.assertEqual(dbmap['schema public']['operator +(text, text)'],
                         expmap)

    def test_map_operator_comment(self):
        "Map a operator comment"
        self.db.execute(CREATE_STMT)
        dbmap = self.db.execute_and_map(COMMENT_STMT)
        self.assertEqual(dbmap['schema public']
                         ['operator +(text, text)']['description'],
                         'Test operator +')


class OperatorToSqlTestCase(PyrseasTestCase):
    """Test SQL generation from input operators"""

    def test_create_operator(self):
        "Create a simple operator"
        self.db.execute_commit(DROP_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({'operator +(text, text)': {
                    'procedure': 'textcat'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_STMT)

    def test_create_operator_rightarg(self):
        "Create a unitary operator with a right argument"
        self.db.execute_commit("DROP OPERATOR IF EXISTS +(NONE, text)")
        inmap = self.std_map()
        inmap['schema public'].update({'operator +(NONE, text)': {
                    'procedure': 'upper'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), "CREATE OPERATOR + ("
                         "PROCEDURE = upper, RIGHTARG = text)")

    def test_create_operator_commutator(self):
        "Create an operator with a commutator"
        self.db.execute_commit("DROP OPERATOR IF EXISTS &&(integer, integer)")
        inmap = self.std_map()
        inmap['schema public'].update({'operator &&(integer, integer)': {
                    'procedure': 'int4pl', 'commutator': 'public.&&'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
                         "CREATE OPERATOR && (PROCEDURE = int4pl, LEFTARG = "
                         "integer, RIGHTARG = integer, COMMUTATOR = "
                         "OPERATOR(public.&&))")

    def test_create_operator_in_schema(self):
        "Create a operator within a non-public schema"
        self.db.execute("CREATE SCHEMA s1")
        inmap = self.std_map()
        inmap.update({'schema s1': {'operator +(text, text)': {
                    'procedure': 'textcat'}}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[1]), "CREATE OPERATOR s1.+ "
                         "(PROCEDURE = textcat, LEFTARG = text, "
                         "RIGHTARG = text)")
        self.db.execute_commit("DROP SCHEMA s1 CASCADE")

    def test_drop_operator(self):
        "Drop an existing operator"
        self.db.execute(DROP_STMT)
        self.db.execute_commit(CREATE_STMT)
        dbsql = self.db.process_map(self.std_map())
        self.assertEqual(dbsql, ["DROP OPERATOR +(text, text)"])

    def test_operator_with_comment(self):
        "Create a operator with a comment"
        self.db.execute_commit(DROP_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({
                'operator +(text, text)': {
                    'description': 'Test operator +',
                    'procedure': 'textcat'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_STMT)
        self.assertEqual(dbsql[1], COMMENT_STMT)

    def test_comment_on_operator(self):
        "Create a comment for an existing operator"
        self.db.execute(DROP_STMT)
        self.db.execute_commit(CREATE_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({
                'operator +(text, text)': {
                    'description': 'Test operator +',
                    'procedure': 'textcat'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [COMMENT_STMT])

    def test_drop_operator_comment(self):
        "Drop a comment on an existing operator"
        self.db.execute(DROP_STMT)
        self.db.execute(CREATE_STMT)
        self.db.execute_commit(COMMENT_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({
                'operator +(text, text)': {
                    'language': 'sql', 'returns': 'integer',
                    'procedure': 'textcat'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql,
                         ["COMMENT ON OPERATOR +(text, text) IS NULL"])

    def test_change_operator_comment(self):
        "Change existing comment on a operator"
        self.db.execute(DROP_STMT)
        self.db.execute(CREATE_STMT)
        self.db.execute_commit(COMMENT_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({
                'operator +(text, text)': {
                    'description': 'Changed operator +',
                    'procedure': 'textcat'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [
                "COMMENT ON OPERATOR +(text, text) IS "
                "'Changed operator +'"])


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(OperatorToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            OperatorToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
