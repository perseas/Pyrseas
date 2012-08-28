# -*- coding: utf-8 -*-
"""Test operator classes"""

import unittest

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

CREATE_TYPE_STMT = """
CREATE TYPE myint;
CREATE FUNCTION myintin(cstring) RETURNS myint AS 'int4in' LANGUAGE internal;
CREATE FUNCTION myintout(myint) RETURNS cstring AS 'int4out' LANGUAGE internal;
CREATE TYPE myint (INPUT = myintin, OUTPUT = myintout);
CREATE FUNCTION myinteq(myint,myint) RETURNS boolean AS 'int4eq'
       LANGUAGE internal;
CREATE FUNCTION myintlt(myint,myint) RETURNS boolean AS 'int4lt'
       LANGUAGE internal;
CREATE OPERATOR < (PROCEDURE = myintlt, LEFTARG = myint, RIGHTARG = myint);
CREATE OPERATOR = (PROCEDURE = myinteq, LEFTARG = myint, RIGHTARG = myint);
CREATE FUNCTION btmyintcmp(myint,myint) RETURNS integer AS 'btint4cmp'
       LANGUAGE internal;
"""

CREATE_STMT = "CREATE OPERATOR CLASS oc1 FOR TYPE integer USING btree " \
    "AS OPERATOR 1 <, OPERATOR 3 =, FUNCTION 1 btint4cmp(integer,integer)"
CREATE_STMT_LONG = "CREATE OPERATOR CLASS oc1 FOR TYPE integer USING btree " \
    "AS OPERATOR 1 <(integer,integer), OPERATOR 3 =(integer,integer), " \
    "FUNCTION 1 btint4cmp(integer,integer)"
DROP_STMT = "DROP OPERATOR CLASS IF EXISTS oc1 USING btree"
COMMENT_STMT = "COMMENT ON OPERATOR CLASS oc1 USING btree IS " \
    "'Test operator class oc1'"


class OperatorClassToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of existing operator classes"""

    superuser = True

    def test_map_operclass(self):
        "Map an operator class"
        dbmap = self.to_map([CREATE_STMT])
        expmap = {'type': 'integer', 'operators': {
                1: '<(integer,integer)', 3: '=(integer,integer)'},
                  'functions': {1: 'btint4cmp(integer,integer)'}}
        self.assertEqual(dbmap['schema public'][
                'operator class oc1 using btree'], expmap)

    def test_map_operclass_default(self):
        "Map a default operator class"
        stmts = [CREATE_TYPE_STMT,
                 CREATE_STMT.replace('integer', 'myint')
                 .replace('int4', 'myint')
                 .replace(' FOR ', ' DEFAULT FOR ')]
        dbmap = self.to_map(stmts)
        expmap = {'type': 'myint', 'default': True,
                  'operators': {1: '<(myint,myint)', 3: '=(myint,myint)'},
                  'functions': {1: 'btmyintcmp(myint,myint)'}}
        self.assertEqual(dbmap['schema public'][
                'operator class oc1 using btree'], expmap)

    def test_map_operclass_comment(self):
        "Map an operator class comment"
        dbmap = self.to_map([CREATE_STMT, COMMENT_STMT])
        self.assertEqual(dbmap['schema public']
                         ['operator class oc1 using btree']['description'],
                         'Test operator class oc1')


class OperatorClassToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation from input operators"""

    def test_create_operclass(self):
        "Create an operator class"
        inmap = self.std_map()
        inmap['schema public'].update({'operator class oc1 using btree': {
                    'type': 'integer', 'operators': {
                        1: '<(integer,integer)', 3: '=(integer,integer)'},
                    'functions': {1: 'btint4cmp(integer,integer)'}}})
        sql = self.to_sql(inmap)
        self.assertEqual(fix_indent(sql[0]), CREATE_STMT_LONG)

    def test_create_operclass_default(self):
        "Create a default operator class"
        inmap = self.std_map()
        inmap['schema public'].update({'operator class oc1 using btree': {
                    'default': True,
                    'type': 'myint', 'operators': {
                        1: '<(myint,myint)', 3: '=(myint,myint)'},
                    'functions': {1: 'btmyintcmp(myint,myint)'}}})
        sql = self.to_sql(inmap, [CREATE_TYPE_STMT], superuser=True)
        self.assertEqual(fix_indent(sql[0]),
                         CREATE_STMT_LONG.replace(' FOR ', ' DEFAULT FOR ')
                         .replace('integer', 'myint').replace('int4', 'myint'))

    def test_create_operclass_in_schema(self):
        "Create a operator within a non-public schema"
        inmap = self.std_map()
        inmap.update({'schema s1': {'operator class oc1 using btree': {
                        'type': 'integer', 'operators': {
                            1: '<(integer,integer)', 3: '=(integer,integer)'},
                        'functions': {1: 'btint4cmp(integer,integer)'}}}})
        sql = self.to_sql(inmap, ["CREATE SCHEMA s1"])
        self.assertEqual(fix_indent(sql[0]), "CREATE OPERATOR CLASS s1.oc1 "
                         "FOR TYPE integer USING btree AS "
                         "OPERATOR 1 <(integer,integer), "
                         "OPERATOR 3 =(integer,integer), "
                         "FUNCTION 1 btint4cmp(integer,integer)")

    def test_drop_operclass(self):
        "Drop an existing operator"
        sql = self.to_sql(self.std_map(), [CREATE_STMT], superuser=True)
        self.assertEqual(sql, ["DROP OPERATOR CLASS oc1 USING btree",
                                 "DROP OPERATOR FAMILY oc1 USING btree"])

    def test_operclass_with_comment(self):
        "Create an operator class with a comment"
        inmap = self.std_map()
        inmap['schema public'].update({'operator class oc1 using btree': {
                    'description': 'Test operator class oc1',
                    'type': 'integer', 'operators': {
                        1: '<(integer,integer)', 3: '=(integer,integer)'},
                    'functions': {1: 'btint4cmp(integer,integer)'}}})
        sql = self.to_sql(inmap)
        self.assertEqual(fix_indent(sql[0]), CREATE_STMT_LONG)
        self.assertEqual(sql[1], COMMENT_STMT)

    def test_comment_on_operclass(self):
        "Create a comment for an existing operator class"
        inmap = self.std_map()
        inmap['schema public'].update({'operator class oc1 using btree': {
                    'description': 'Test operator class oc1',
                    'type': 'integer', 'operators': {
                        1: '<(integer,integer)', 3: '=(integer,integer)'},
                    'functions': {1: 'btint4cmp(integer,integer)'}},
                                       'operator family oc1 using btree': {}})
        sql = self.to_sql(inmap, [CREATE_STMT], superuser=True)
        self.assertEqual(sql, [COMMENT_STMT])

    def test_drop_operclass_comment(self):
        "Drop the existing comment on an operator class"
        stmts = [CREATE_STMT, COMMENT_STMT]
        inmap = self.std_map()
        inmap['schema public'].update({'operator class oc1 using btree': {
                    'type': 'integer', 'operators': {
                        1: '<(integer,integer)', 3: '=(integer,integer)'},
                    'functions': {1: 'btint4cmp(integer,integer)'}},
                                       'operator family oc1 using btree': {}})
        sql = self.to_sql(inmap, stmts, superuser=True)
        self.assertEqual(sql, [
                "COMMENT ON OPERATOR CLASS oc1 USING btree IS NULL"])

    def test_change_operclass_comment(self):
        "Change existing comment on an operator class"
        stmts = [CREATE_STMT, COMMENT_STMT]
        inmap = self.std_map()
        inmap['schema public'].update({'operator class oc1 using btree': {
                    'description': 'Changed operator class oc1',
                    'type': 'integer', 'operators': {
                        1: '<(integer,integer)', 3: '=(integer,integer)'},
                    'functions': {1: 'btint4cmp(integer,integer)'}},
                                       'operator family oc1 using btree': {}})
        sql = self.to_sql(inmap, stmts, superuser=True)
        self.assertEqual(sql, [
                "COMMENT ON OPERATOR CLASS oc1 USING btree IS "
                "'Changed operator class oc1'"])


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(
        OperatorClassToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            OperatorClassToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
