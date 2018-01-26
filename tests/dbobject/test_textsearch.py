# -*- coding: utf-8 -*-
"""Test text search objects"""

import pytest

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

CREATE_TSC_STMT = "CREATE TEXT SEARCH CONFIGURATION sd.tsc1 (PARSER = tsp1)"
CREATE_TSD_STMT = "CREATE TEXT SEARCH DICTIONARY sd.tsd1 (TEMPLATE = simple, "\
    "stopwords = 'english')"
CREATE_TSP_STMT = "CREATE TEXT SEARCH PARSER sd.tsp1 (START = prsd_start, " \
    "GETTOKEN = prsd_nexttoken, END = prsd_end, LEXTYPES = prsd_lextype, " \
    "HEADLINE = prsd_headline)"
CREATE_TST_STMT = "CREATE TEXT SEARCH TEMPLATE sd.tst1 (INIT = dsimple_init, "\
    "LEXIZE = dsimple_lexize)"
COMMENT_TSC_STMT = "COMMENT ON TEXT SEARCH CONFIGURATION sd.tsc1 IS " \
    "'Test configuration tsc1'"
COMMENT_TSD_STMT = "COMMENT ON TEXT SEARCH DICTIONARY sd.tsd1 IS " \
    "'Test dictionary tsd1'"
COMMENT_TSP_STMT = "COMMENT ON TEXT SEARCH PARSER sd.tsp1 IS " \
                   "'Test parser tsp1'"
COMMENT_TST_STMT = "COMMENT ON TEXT SEARCH TEMPLATE sd.tst1 IS " \
    "'Test template tst1'"


class TextSearchConfigToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of existing text search configurations"""

    superuser = True

    def test_map_ts_config(self):
        "Map an existing text search configuration"
        stmts = [CREATE_TSP_STMT, CREATE_TSC_STMT]
        dbmap = self.to_map(stmts)
        assert dbmap['schema sd']['text search configuration tsc1'] == {
            'parser': 'tsp1'}

    def test_map_cross_schema_ts_config(self):
        "Map a text search config with parser in different schema"
        stmts = ["CREATE SCHEMA s1",
                 "CREATE TEXT SEARCH PARSER s1.tsp1 "
                 "(START = prsd_start, GETTOKEN = prsd_nexttoken, "
                 "END = prsd_end, LEXTYPES = prsd_lextype)",
                 "CREATE TEXT SEARCH CONFIGURATION tsc1 (PARSER = s1.tsp1)"]
        dbmap = self.to_map(stmts)
        assert dbmap['schema sd']['text search configuration tsc1'] == {
            'parser': 's1.tsp1'}

    def test_map_ts_config_comment(self):
        "Map a text search configuration with a comment"
        stmts = [CREATE_TSP_STMT, CREATE_TSC_STMT, COMMENT_TSC_STMT]
        dbmap = self.to_map(stmts)
        assert dbmap['schema sd']['text search configuration tsc1'][
            'description'] == 'Test configuration tsc1'


class TextSearchConfigToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation for input text search configurations"""

    def test_create_ts_config(self):
        "Create a text search configuration that didn't exist"
        inmap = self.std_map()
        inmap['schema sd'].update({'text search parser tsp1': {
            'start': 'prsd_start', 'gettoken': 'prsd_nexttoken',
            'end': 'prsd_end', 'lextypes': 'prsd_lextype',
            'headline': 'prsd_headline'}, 'text search configuration tsc1': {
                'parser': 'tsp1'}})
        sql = self.to_sql(inmap, [CREATE_TSP_STMT])
        assert fix_indent(sql[0]) == CREATE_TSC_STMT

    def test_create_ts_config_in_schema(self):
        "Create a text search config with parser in non-default schema"
        inmap = self.std_map()
        inmap.update({'schema s1': {'text search parser tsp1': {
            'start': 'prsd_start', 'gettoken': 'prsd_nexttoken',
            'end': 'prsd_end', 'lextypes': 'prsd_lextype'}}})
        inmap['schema sd'].update({'text search configuration tsc1': {
            'parser': 's1.tsp1'}})
        sql = self.to_sql(inmap, ["CREATE SCHEMA s1"])
        assert fix_indent(sql[0]) == "CREATE TEXT SEARCH PARSER s1.tsp1 " \
            "(START = prsd_start, GETTOKEN = prsd_nexttoken, " \
            "END = prsd_end, LEXTYPES = prsd_lextype)"
        assert fix_indent(sql[1]) == \
            "CREATE TEXT SEARCH CONFIGURATION sd.tsc1 (PARSER = s1.tsp1)"

    def test_bad_map_ts_config_(self):
        "Error creating a text search configuration with a bad map"
        inmap = self.std_map()
        inmap['schema sd'].update({'tsc1': {'parser': 'tsp1'}})
        with pytest.raises(KeyError):
            self.to_sql(inmap)

    def test_drop_ts_config(self):
        "Drop an existing text search configuration"
        stmts = [CREATE_TSP_STMT, CREATE_TSC_STMT]
        sql = self.to_sql(self.std_map(), stmts, superuser=True)
        assert sql[0] == "DROP TEXT SEARCH CONFIGURATION sd.tsc1"
        assert sql[1] == "DROP TEXT SEARCH PARSER sd.tsp1"

    def test_comment_on_ts_config(self):
        "Create a comment for an existing text search configuration"
        stmts = [CREATE_TSP_STMT, CREATE_TSC_STMT]
        inmap = self.std_map()
        inmap['schema sd'].update({'text search configuration tsc1': {
            'parser': 'tsp1', 'description': "Test configuration tsc1"},
            'text search parser tsp1': {
                'start': 'prsd_start', 'gettoken': 'prsd_nexttoken',
                'end': 'prsd_end', 'lextypes': 'prsd_lextype',
                'headline': 'prsd_headline'}})
        sql = self.to_sql(inmap, stmts, superuser=True)
        assert sql == [COMMENT_TSC_STMT]


class TextSearchDictToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of existing text search dictionaries"""

    def test_map_ts_dict(self):
        "Map an existing text search dictionary"
        dbmap = self.to_map([CREATE_TSD_STMT])
        assert dbmap['schema sd']['text search dictionary tsd1'] == {
            'template': 'simple', 'options': "stopwords = 'english'"}

    def test_map_ts_dict_comment(self):
        "Map a text search dictionary with a comment"
        stmts = [CREATE_TSD_STMT, COMMENT_TSD_STMT]
        dbmap = self.to_map(stmts)
        assert dbmap['schema sd']['text search dictionary tsd1'][
            'description'], 'Test dictionary tsd1'


class TextSearchDictToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation for input text search dictionaries"""

    def test_create_ts_dict(self):
        "Create a text search dictionary that didn't exist"
        inmap = self.std_map()
        inmap['schema sd'].update({'text search dictionary tsd1': {
            'template': 'simple', 'options': "stopwords = 'english'"}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == CREATE_TSD_STMT

    def test_bad_map_ts_dict(self):
        "Error creating a text search dictionary with a bad map"
        inmap = self.std_map()
        inmap['schema sd'].update({'tsd1': {
            'template': 'simple', 'options': "stopwords = 'english'"}})
        with pytest.raises(KeyError):
            self.to_sql(inmap)

    def test_drop_ts_dict(self):
        "Drop an existing text search dictionary"
        sql = self.to_sql(self.std_map(), [CREATE_TSD_STMT])
        assert sql == ["DROP TEXT SEARCH DICTIONARY sd.tsd1"]

    def test_comment_on_ts_dict(self):
        "Create a comment for an existing text search dictionary"
        inmap = self.std_map()
        inmap['schema sd'].update({'text search dictionary tsd1': {
            'template': 'simple', 'options': "stopwords = 'english'",
            'description': "Test dictionary tsd1"}})
        sql = self.to_sql(inmap, [CREATE_TSD_STMT])
        assert sql == [COMMENT_TSD_STMT]


class TextSearchParserToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of existing text search parsers"""

    superuser = True

    def test_map_ts_parser(self):
        "Map an existing text search parser"
        stmts = [CREATE_TSP_STMT]
        dbmap = self.to_map(stmts)
        assert dbmap['schema sd']['text search parser tsp1'] == {
            'start': 'prsd_start', 'gettoken': 'prsd_nexttoken',
            'end': 'prsd_end', 'lextypes': 'prsd_lextype',
            'headline': 'prsd_headline'}

    def test_map_ts_parser_comment(self):
        "Map a text search parser with a comment"
        stmts = [CREATE_TSP_STMT, COMMENT_TSP_STMT]
        dbmap = self.to_map(stmts)
        assert dbmap['schema sd']['text search parser tsp1'][
            'description'] == 'Test parser tsp1'


class TextSearchParserToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation for input text search parsers"""

    def test_create_ts_parser(self):
        "Create a text search parser that didn't exist"
        inmap = self.std_map()
        inmap['schema sd'].update({'text search parser tsp1': {
            'start': 'prsd_start', 'gettoken': 'prsd_nexttoken',
            'end': 'prsd_end', 'lextypes': 'prsd_lextype',
            'headline': 'prsd_headline'}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == CREATE_TSP_STMT

    def test_bad_map_ts_parser(self):
        "Error creating a text search parser with a bad map"
        inmap = self.std_map()
        inmap['schema sd'].update({'tsp1': {
            'start': 'prsd_start', 'gettoken': 'prsd_nexttoken',
            'end': 'prsd_end', 'lextypes': 'prsd_lextype'}})
        with pytest.raises(KeyError):
            self.to_sql(inmap)

    def test_drop_ts_parser(self):
        "Drop an existing text search parser"
        sql = self.to_sql(self.std_map(), [CREATE_TSP_STMT], superuser=True)
        assert sql == ["DROP TEXT SEARCH PARSER sd.tsp1"]

    def test_comment_on_ts_parser(self):
        "Create a comment for an existing text search parser"
        inmap = self.std_map()
        inmap['schema sd'].update({'text search parser tsp1': {
            'start': 'prsd_start', 'gettoken': 'prsd_nexttoken',
            'end': 'prsd_end', 'lextypes': 'prsd_lextype',
            'headline': 'prsd_headline', 'description': "Test parser tsp1"}})
        sql = self.to_sql(inmap, [CREATE_TSP_STMT], superuser=True)
        assert sql == [COMMENT_TSP_STMT]


class TextSearchTemplateToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of existing text search templates"""

    superuser = True

    def test_map_ts_template(self):
        "Map an existing text search template"
        dbmap = self.to_map([CREATE_TST_STMT])
        assert dbmap['schema sd']['text search template tst1'] == {
            'init': 'dsimple_init', 'lexize': 'dsimple_lexize'}

    def test_map_ts_template_comment(self):
        "Map a text search template with a comment"
        stmts = [CREATE_TST_STMT, COMMENT_TST_STMT]
        dbmap = self.to_map(stmts)
        assert dbmap['schema sd']['text search template tst1'][
            'description'], 'Test template tst1'


class TextSearchTemplateToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation for input text search templates"""

    def test_create_ts_template(self):
        "Create a text search template that didn't exist"
        inmap = self.std_map()
        inmap['schema sd'].update({'text search template tst1': {
            'init': 'dsimple_init', 'lexize': 'dsimple_lexize'}})
        sql = self.to_sql(inmap, superuser=True)
        assert fix_indent(sql[0]) == CREATE_TST_STMT

    def test_bad_map_ts_template(self):
        "Error creating a text search template with a bad map"
        inmap = self.std_map()
        inmap['schema sd'].update({'tst1': {
            'init': 'dsimple_init', 'lexize': 'dsimple_lexize'}})
        with pytest.raises(KeyError):
            self.to_sql(inmap)

    def test_drop_ts_template(self):
        "Drop an existing text search template"
        sql = self.to_sql(self.std_map(), [CREATE_TST_STMT], superuser=True)
        assert sql == ["DROP TEXT SEARCH TEMPLATE sd.tst1"]

    def test_comment_on_ts_template(self):
        "Create a comment for an existing text search template"
        inmap = self.std_map()
        inmap['schema sd'].update({'text search template tst1': {
            'init': 'dsimple_init', 'lexize': 'dsimple_lexize',
            'description': "Test template tst1"}})
        sql = self.to_sql(inmap, [CREATE_TST_STMT], superuser=True)
        assert sql == [COMMENT_TST_STMT]
