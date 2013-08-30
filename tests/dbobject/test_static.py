# -*- coding: utf-8 -*-
"""Test loading of data into static tables"""

from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

CREATE_STMT = "CREATE TABLE t1 (c1 integer, c2 text)"
TRUNC_STMT = "TRUNCATE ONLY t1"
COPY_STMT = "\\copy t1 from 't1.data' csv"


class StaticTableToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation of table load statements"""

    def test_load_static_table(self):
        "Truncate and load a two-column table"
        inmap = self.std_map()
        inmap['schema public'].update({'table t1': {
            'columns': [{'c1': {'type': 'integer'}},
                        {'c2': {'type': 'text'}}]}})
        cfg = {'dataload': {'schema public': ['t1']}}
        sql = self.to_sql(inmap, [CREATE_STMT], config=cfg)
        assert fix_indent(sql[0]) == TRUNC_STMT
        assert fix_indent(sql[1]) == COPY_STMT
