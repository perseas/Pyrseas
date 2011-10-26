# -*- coding: utf-8 -*-
"""Test text search objects"""

import unittest

from utils import PyrseasTestCase, fix_indent

CREATE_TSP_STMT = "CREATE TEXT SEARCH PARSER tsp1 (START = prsd_start, " \
    "GETTOKEN = prsd_nexttoken, END = prsd_end, LEXTYPES = prsd_lextype, " \
    "HEADLINE = prsd_headline)"
DROP_TSP_STMT = "DROP TEXT SEARCH PARSER IF EXISTS tsp1 CASCADE"
COMMENT_TSP_STMT = "COMMENT ON TEXT SEARCH PARSER tsp1 IS 'Test parser tsp1'"


class TextSearchParserToMapTestCase(PyrseasTestCase):
    """Test mapping of existing text search parsers"""

    def test_map_ts_parser(self):
        "Map an existing text search parser"
        self.db.execute(DROP_TSP_STMT)
        dbmap = self.db.execute_and_map(CREATE_TSP_STMT)
        self.assertEqual(dbmap['schema public']['text search parser tsp1'], {
                'start': 'prsd_start', 'gettoken': 'prsd_nexttoken',
                'end': 'prsd_end', 'lextypes': 'prsd_lextype',
                'headline': 'prsd_headline'})

    def test_map_ts_parser_comment(self):
        "Map a text search parser with a comment"
        self.db.execute(DROP_TSP_STMT)
        self.db.execute(CREATE_TSP_STMT)
        dbmap = self.db.execute_and_map(COMMENT_TSP_STMT)
        self.assertEqual(dbmap['schema public']['text search parser tsp1']
                         ['description'], 'Test parser tsp1')


class TextSearchParserToSqlTestCase(PyrseasTestCase):
    """Test SQL generation for input text search parsers"""

    def tearDown(self):
        self.db.execute_commit(DROP_TSP_STMT)
        self.db.close()

    def test_create_ts_parser(self):
        "Create a text search parser that didn't exist"
        inmap = self.std_map()
        inmap['schema public'].update({'text search parser tsp1': {
                'start': 'prsd_start', 'gettoken': 'prsd_nexttoken',
                'end': 'prsd_end', 'lextypes': 'prsd_lextype',
                'headline': 'prsd_headline'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_TSP_STMT)

    def test_bad_ts_parser_map(self):
        "Error creating a text search parser with a bad map"
        inmap = self.std_map()
        inmap['schema public'].update({'tsp1': {
                'start': 'prsd_start', 'gettoken': 'prsd_nexttoken',
                'end': 'prsd_end', 'lextypes': 'prsd_lextype'}})
        self.assertRaises(KeyError, self.db.process_map, inmap)

    def test_drop_ts_parser(self):
        "Drop an existing text search parser"
        self.db.execute_commit(CREATE_TSP_STMT)
        dbsql = self.db.process_map(self.std_map())
        self.assertEqual(dbsql, ["DROP TEXT SEARCH PARSER tsp1"])

    def test_comment_on_ts_parser(self):
        "Create a comment for an existing text search parser"
        self.db.execute_commit(CREATE_TSP_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({'text search parser tsp1': {
                'start': 'prsd_start', 'gettoken': 'prsd_nexttoken',
                'end': 'prsd_end', 'lextypes': 'prsd_lextype',
                'headline': 'prsd_headline',
                'description': "Test parser tsp1"}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [COMMENT_TSP_STMT])


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(
        TextSearchParserToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            TextSearchParserToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
