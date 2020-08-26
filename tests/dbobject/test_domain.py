# -*- coding: utf-8 -*-
"""Test domains"""

from pyrseas.testutils import DatabaseToMapTestCase
from pyrseas.testutils import InputMapToSqlTestCase, fix_indent

CREATEFUNC_STMT = ("CREATE FUNCTION sd.dc1(integer) RETURNS bool LANGUAGE sql "
                   "IMMUTABLE AS $_$select true$_$")
CREATE_STMT = "CREATE DOMAIN sd.d1 AS integer"
DROP_STMT = "DROP DOMAIN IF EXISTS d1"
COMMENT_STMT = "COMMENT ON DOMAIN d1 IS 'Test domain d1'"


class DomainToMapTestCase(DatabaseToMapTestCase):
    """Test mapping of created domains"""

    def test_domain(self):
        "Map a simple domain"
        dbmap = self.to_map([CREATE_STMT])
        assert dbmap['schema sd']['domain d1'] == {'type': 'integer'}

    def test_domain_not_null(self):
        "Map a domain with a NOT NULL constraint"
        dbmap = self.to_map([CREATE_STMT + " NOT NULL"])
        expmap = {'type': 'integer', 'not_null': True}
        assert dbmap['schema sd']['domain d1'] == expmap

    def test_domain_default(self):
        "Map a domain with a DEFAULT"
        dbmap = self.to_map(["CREATE DOMAIN d1 AS date DEFAULT CURRENT_DATE"])
        expmap = {'type': 'date', 'default': 'CURRENT_DATE'}
        if self.db.version < 100000:
            expmap['default'] = "('now'::text)::date"
        assert dbmap['schema sd']['domain d1'] == expmap

    def test_domain_check(self):
        "Map a domain with a CHECK constraint"
        dbmap = self.to_map([CREATE_STMT + " CHECK (VALUE >= 1888)"])
        expmap = {'type': 'integer', 'check_constraints': {
            'd1_check': {'expression': '(VALUE >= 1888)'}}}
        assert dbmap['schema sd']['domain d1'] == expmap

    def test_domain_depend_function(self):
        "A domain is created after a function it depends on"
        dbmap = self.to_map([CREATEFUNC_STMT,
                             CREATE_STMT + " CHECK (dc1(VALUE))"])
        expmap = {'type': 'integer',
                  'check_constraints': {
                      'd1_check': {
                          'expression': 'sd.dc1(VALUE)',
                          'depends_on': ['function dc1(integer)']}}}
        assert dbmap['schema sd']['domain d1'] == expmap


class DomainToSqlTestCase(InputMapToSqlTestCase):
    """Test SQL generation from input domains"""

    def test_create_domain_simple(self):
        "Create a simple domain"
        inmap = self.std_map()
        inmap['schema sd'].update({'domain d1': {'type': 'integer'}})
        sql = self.to_sql(inmap)
        assert sql == [CREATE_STMT]

    def test_create_domain_default(self):
        "Create a domain with a DEFAULT and NOT NULL"
        inmap = self.std_map()
        inmap['schema sd'].update({'domain d1': {
            'type': 'integer', 'not_null': True, 'default': 0}})
        sql = self.to_sql(inmap)
        assert sql == [CREATE_STMT + " NOT NULL DEFAULT 0"]

    def test_create_domain_check(self):
        "Create a domain with a CHECK constraint"
        inmap = self.std_map()
        inmap['schema sd'].update({'domain d1': {
            'type': 'integer', 'check_constraints': {'d1_check': {
                'expression': '(VALUE >= 1888)'}}}})
        sql = self.to_sql(inmap)
        assert fix_indent(sql[0]) == CREATE_STMT
        assert fix_indent(sql[1]) == "ALTER DOMAIN sd.d1 ADD CONSTRAINT " + \
            "d1_check CHECK (VALUE >= 1888)"

    def test_add_domain_check(self):
        "Add a CHECK constraint to a domain"
        inmap = self.std_map()
        inmap['schema sd'].update({'domain d1': {
            'type': 'integer', 'check_constraints': {'d1_check': {
                'expression': '(VALUE >= 1888)'}}}})
        sql = self.to_sql(inmap, [CREATE_STMT])
        assert fix_indent(sql[0]) == "ALTER DOMAIN sd.d1 " + \
            "ADD CONSTRAINT d1_check CHECK (VALUE >= 1888)"

    def test_drop_domain(self):
        "Drop an existing domain"
        sql = self.to_sql(self.std_map(), [CREATE_STMT])
        assert sql == ["DROP DOMAIN sd.d1"]

    def test_rename_domain(self):
        "Rename an existing domain"
        inmap = self.std_map()
        inmap['schema sd'].update({'domain d2': {
            'oldname': 'd1', 'type': 'integer'}})
        sql = self.to_sql(inmap, [CREATE_STMT])
        assert sql == ["ALTER DOMAIN sd.d1 RENAME TO d2"]

    def test_create_domain_before_function(self):
        "Check that the domain is created after a function it depends on"
        inmap = self.std_map()
        inmap['schema sd'].update({'domain d1': {
            'type': 'integer', 'check_constraints': {
                'd1_check': {'expression': 'dc1(VALUE)',
                             'depends_on': ['function dc1(integer)']}}},
            'function dc1(integer)': {
                'language': 'sql', 'returns': 'bool',
                'source': 'select true', 'volatility': 'immutable'}})
        sql = self.to_sql(inmap)
        assert len(sql) == 4
        assert sql[1] == CREATE_STMT
        assert fix_indent(sql[2]) == CREATEFUNC_STMT
        assert sql[3].startswith("ALTER DOMAIN sd.d1 ADD CONSTRAINT")
