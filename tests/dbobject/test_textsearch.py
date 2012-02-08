# -*- coding: utf-8 -*-
"""Test text search objects"""

import unittest

from pyrseas.testutils import PyrseasTestCase, fix_indent

CREATE_TSC_STMT = "CREATE TEXT SEARCH CONFIGURATION tsc1 (PARSER = tsp1)"
CREATE_TSD_STMT = "CREATE TEXT SEARCH DICTIONARY tsd1 (TEMPLATE = simple, " \
    "stopwords = 'english')"
CREATE_TSP_STMT = "CREATE TEXT SEARCH PARSER tsp1 (START = prsd_start, " \
    "GETTOKEN = prsd_nexttoken, END = prsd_end, LEXTYPES = prsd_lextype, " \
    "HEADLINE = prsd_headline)"
CREATE_TST_STMT = "CREATE TEXT SEARCH TEMPLATE tst1 (INIT = dsimple_init, " \
    "LEXIZE = dsimple_lexize)"
DROP_TSC_STMT = "DROP TEXT SEARCH CONFIGURATION IF EXISTS tsc1"
DROP_TSD_STMT = "DROP TEXT SEARCH DICTIONARY IF EXISTS tsd1"
DROP_TSP_STMT = "DROP TEXT SEARCH PARSER IF EXISTS tsp1 CASCADE"
DROP_TST_STMT = "DROP TEXT SEARCH TEMPLATE IF EXISTS tst1"
COMMENT_TSC_STMT = "COMMENT ON TEXT SEARCH CONFIGURATION tsc1 IS " \
    "'Test configuration tsc1'"
COMMENT_TSD_STMT = "COMMENT ON TEXT SEARCH DICTIONARY tsd1 IS " \
    "'Test dictionary tsd1'"
COMMENT_TSP_STMT = "COMMENT ON TEXT SEARCH PARSER tsp1 IS 'Test parser tsp1'"
COMMENT_TST_STMT = "COMMENT ON TEXT SEARCH TEMPLATE tst1 IS " \
    "'Test template tst1'"


class TextSearchConfigToMapTestCase(PyrseasTestCase):
    """Test mapping of existing text search configurations"""

    def tearDown(self):
        self.db.execute(DROP_TSC_STMT)
        self.db.execute_commit(DROP_TSP_STMT)
        self.db.close()

    def test_map_ts_config(self):
        "Map an existing text search configuration"
        self.db.execute(DROP_TSC_STMT)
        self.db.execute(DROP_TSP_STMT)
        self.db.execute(CREATE_TSP_STMT)
        dbmap = self.db.execute_and_map(CREATE_TSC_STMT)
        self.assertEqual(dbmap['schema public']
                         ['text search configuration tsc1'], {
                'parser': 'tsp1'})

    def test_map_cross_schema_ts_config(self):
        "Map a text search config with parser in different schema"
        self.db.execute("DROP SCHEMA IF EXISTS s1 CASCADE")
        self.db.execute("CREATE SCHEMA s1")
        self.db.execute("CREATE TEXT SEARCH PARSER s1.tsp1 "
                        "(START = prsd_start, GETTOKEN = prsd_nexttoken, "
                        "END = prsd_end, LEXTYPES = prsd_lextype)")
        self.db.execute(DROP_TSC_STMT)
        dbmap = self.db.execute_and_map(
                "CREATE TEXT SEARCH CONFIGURATION tsc1 (PARSER = s1.tsp1)")
        self.assertEqual(dbmap['schema public']
                         ['text search configuration tsc1'], {
                'parser': 's1.tsp1'})
        self.db.execute_commit("DROP SCHEMA s1 CASCADE")

    def test_map_ts_config_comment(self):
        "Map a text search configuration with a comment"
        self.db.execute(DROP_TSC_STMT)
        self.db.execute(DROP_TSP_STMT)
        self.db.execute(CREATE_TSP_STMT)
        self.db.execute(CREATE_TSC_STMT)
        dbmap = self.db.execute_and_map(COMMENT_TSC_STMT)
        self.assertEqual(dbmap['schema public']
                         ['text search configuration tsc1']['description'],
                         'Test configuration tsc1')


class TextSearchConfigToSqlTestCase(PyrseasTestCase):
    """Test SQL generation for input text search configurations"""

    def tearDown(self):
        self.db.execute(DROP_TSC_STMT)
        self.db.execute_commit(DROP_TSP_STMT)
        self.db.close()

    def test_create_ts_config(self):
        "Create a text search configuration that didn't exist"
        inmap = self.std_map()
        inmap['schema public'].update({'text search configuration tsc1': {
                    'parser': 'tsp1'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_TSC_STMT)

    def test_create_cross_schema_ts_config(self):
        "Create a text search config with parser in different schema"
        self.db.execute_commit("CREATE SCHEMA s1")
        inmap = self.std_map()
        inmap.update({'schema s1': {'text search parser tsp1': {
                'start': 'prsd_start', 'gettoken': 'prsd_nexttoken',
                'end': 'prsd_end', 'lextypes': 'prsd_lextype'}}})
        inmap['schema public'].update({'text search configuration tsc1': {
                'parser': 's1.tsp1'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]),
                         "CREATE TEXT SEARCH PARSER s1.tsp1 "
                         "(START = prsd_start, GETTOKEN = prsd_nexttoken, "
                         "END = prsd_end, LEXTYPES = prsd_lextype)")
        self.assertEqual(fix_indent(dbsql[1]),
                "CREATE TEXT SEARCH CONFIGURATION tsc1 (PARSER = s1.tsp1)")
        self.db.execute_commit("DROP SCHEMA s1 CASCADE")

    def test_bad_map_ts_config_(self):
        "Error creating a text search configuration with a bad map"
        inmap = self.std_map()
        inmap['schema public'].update({'tsc1': {'parser': 'tsp1'}})
        self.assertRaises(KeyError, self.db.process_map, inmap)

    def test_drop_ts_config(self):
        "Drop an existing text search configuration"
        self.db.execute(CREATE_TSP_STMT)
        self.db.execute_commit(CREATE_TSC_STMT)
        dbsql = self.db.process_map(self.std_map())
        self.assertEqual(dbsql[0], "DROP TEXT SEARCH PARSER tsp1")
        self.assertEqual(dbsql[1], "DROP TEXT SEARCH CONFIGURATION tsc1")

    def test_comment_on_ts_config(self):
        "Create a comment for an existing text search configuration"
        self.db.execute(CREATE_TSP_STMT)
        self.db.execute_commit(CREATE_TSC_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({'text search configuration tsc1': {
                    'parser': 'tsp1',
                    'description': "Test configuration tsc1"},
                                       'text search parser tsp1': {
                    'start': 'prsd_start', 'gettoken': 'prsd_nexttoken',
                    'end': 'prsd_end', 'lextypes': 'prsd_lextype',
                    'headline': 'prsd_headline'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [COMMENT_TSC_STMT])


class TextSearchDictToMapTestCase(PyrseasTestCase):
    """Test mapping of existing text search dictionaries"""

    def tearDown(self):
        self.db.execute_commit(DROP_TSD_STMT)
        self.db.close()

    def test_map_ts_dict(self):
        "Map an existing text search dictionary"
        self.db.execute(DROP_TSD_STMT)
        dbmap = self.db.execute_and_map(CREATE_TSD_STMT)
        self.assertEqual(dbmap['schema public']
                         ['text search dictionary tsd1'], {
                'template': 'simple', 'options': "stopwords = 'english'"})

    def test_map_ts_dict_comment(self):
        "Map a text search dictionary with a comment"
        self.db.execute(DROP_TSD_STMT)
        self.db.execute(CREATE_TSD_STMT)
        dbmap = self.db.execute_and_map(COMMENT_TSD_STMT)
        self.assertEqual(dbmap['schema public']['text search dictionary tsd1']
                         ['description'], 'Test dictionary tsd1')


class TextSearchDictToSqlTestCase(PyrseasTestCase):
    """Test SQL generation for input text search dictionaries"""

    def tearDown(self):
        self.db.execute_commit(DROP_TSD_STMT)
        self.db.close()

    def test_create_ts_dict(self):
        "Create a text search dictionary that didn't exist"
        inmap = self.std_map()
        inmap['schema public'].update({'text search dictionary tsd1': {
                'template': 'simple', 'options': "stopwords = 'english'"}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_TSD_STMT)

    def test_bad_map_ts_dict(self):
        "Error creating a text search dictionary with a bad map"
        inmap = self.std_map()
        inmap['schema public'].update({'tsd1': {
                'template': 'simple', 'options': "stopwords = 'english'"}})
        self.assertRaises(KeyError, self.db.process_map, inmap)

    def test_drop_ts_dict(self):
        "Drop an existing text search dictionary"
        self.db.execute_commit(CREATE_TSD_STMT)
        dbsql = self.db.process_map(self.std_map())
        self.assertEqual(dbsql, ["DROP TEXT SEARCH DICTIONARY tsd1"])

    def test_comment_on_ts_dict(self):
        "Create a comment for an existing text search dictionary"
        self.db.execute_commit(CREATE_TSD_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({'text search dictionary tsd1': {
                'template': 'simple', 'options': "stopwords = 'english'",
                'description': "Test dictionary tsd1"}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [COMMENT_TSD_STMT])


class TextSearchParserToMapTestCase(PyrseasTestCase):
    """Test mapping of existing text search parsers"""

    def tearDown(self):
        self.db.execute_commit(DROP_TSP_STMT)
        self.db.close()

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

    def test_bad_map_ts_parser(self):
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


class TextSearchTemplateToMapTestCase(PyrseasTestCase):
    """Test mapping of existing text search templates"""

    def test_map_ts_template(self):
        "Map an existing text search template"
        self.db.execute(DROP_TST_STMT)
        dbmap = self.db.execute_and_map(CREATE_TST_STMT)
        self.assertEqual(dbmap['schema public']['text search template tst1'], {
                'init': 'dsimple_init', 'lexize': 'dsimple_lexize'})

    def test_map_ts_template_comment(self):
        "Map a text search template with a comment"
        self.db.execute(DROP_TST_STMT)
        self.db.execute(CREATE_TST_STMT)
        dbmap = self.db.execute_and_map(COMMENT_TST_STMT)
        self.assertEqual(dbmap['schema public']['text search template tst1']
                         ['description'], 'Test template tst1')


class TextSearchTemplateToSqlTestCase(PyrseasTestCase):
    """Test SQL generation for input text search templates"""

    def tearDown(self):
        self.db.execute_commit(DROP_TST_STMT)
        self.db.close()

    def test_create_ts_template(self):
        "Create a text search template that didn't exist"
        self.db.execute_commit(DROP_TST_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({'text search template tst1': {
                    'init': 'dsimple_init', 'lexize': 'dsimple_lexize'}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(fix_indent(dbsql[0]), CREATE_TST_STMT)

    def test_bad_map_ts_template(self):
        "Error creating a text search template with a bad map"
        inmap = self.std_map()
        inmap['schema public'].update({'tst1': {
                    'init': 'dsimple_init', 'lexize': 'dsimple_lexize'}})
        self.assertRaises(KeyError, self.db.process_map, inmap)

    def test_drop_ts_template(self):
        "Drop an existing text search template"
        self.db.execute_commit(CREATE_TST_STMT)
        dbsql = self.db.process_map(self.std_map())
        self.assertEqual(dbsql, ["DROP TEXT SEARCH TEMPLATE tst1"])

    def test_comment_on_ts_template(self):
        "Create a comment for an existing text search template"
        self.db.execute_commit(CREATE_TST_STMT)
        inmap = self.std_map()
        inmap['schema public'].update({'text search template tst1': {
                    'init': 'dsimple_init', 'lexize': 'dsimple_lexize',
                    'description': "Test template tst1"}})
        dbsql = self.db.process_map(inmap)
        self.assertEqual(dbsql, [COMMENT_TST_STMT])


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(
        TextSearchConfigToMapTestCase)
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            TextSearchConfigToSqlTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            TextSearchDictToMapTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            TextSearchDictToSqlTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            TextSearchParserToMapTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            TextSearchParserToSqlTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            TextSearchTemplateToMapTestCase))
    tests.addTest(unittest.TestLoader().loadTestsFromTestCase(
            TextSearchTemplateToSqlTestCase))
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
