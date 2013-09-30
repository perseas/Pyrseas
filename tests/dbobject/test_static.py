# -*- coding: utf-8 -*-
"""Test loading of data into static tables"""
import os

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

CREATE_STMT = "CREATE TABLE t1 (c1 integer, c2 text)"
TRUNC_STMT = "TRUNCATE ONLY t1"
FILE_PATH = 'table.t1.data'
COPY_STMT = "\\copy t1 from '%s' csv" % FILE_PATH
TABLE_DATA = [(1, 'abc'), (2, 'def'), (3, 'ghi')]


class StaticTableToMapTestCase(DatabaseToMapTestCase):
    """Test mapping and copying out of created tables"""

    def test_copy_static_table(self):
        "Copy a two-column table to a file"
        if os.path.exists(FILE_PATH):
            os.remove(FILE_PATH)
        self.db.execute(CREATE_STMT)
        for row in TABLE_DATA:
            self.db.execute("INSERT INTO t1 VALUES (%s, %s)", row)
        cfg = {'datacopy': {'schema public': ['t1']}}
        dbmap = self.to_map([], config=cfg)
        assert dbmap['schema public']['table t1'] == {
            'columns': [{'c1': {'type': 'integer'}}, {'c2': {'type': 'text'}}]}
        recs = []
        with open(os.path.join(
                self.cfg['files']['data_path'], self.cfg['repository']['data'],
                "schema.public", FILE_PATH)) as f:
            for line in f:
                (c1, c2) = line.split(',')
                recs.append((int(c1), c2.rstrip()))
        assert recs == TABLE_DATA


class StaticTableToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation of table load statements"""

    def test_load_static_table(self):
        "Truncate and load a two-column table"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}},
                        {'c2': {'type': 'text'}}]}})
        cfg = {'datacopy': {'schema public': ['t1']}}
        sql = self.to_sql(inmap, [CREATE_STMT], config=cfg)
        assert fix_indent(sql[0]) == TRUNC_STMT
        assert fix_indent(sql[1]) == COPY_STMT
