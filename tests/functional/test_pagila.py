# -*- coding: utf-8 -*-
"""Test dbtoyaml and yamltodb using pagila schema

See http://cvs.pgfoundry.org/cgi-bin/cvsweb.cgi/dbsamples/pagila/
pagila-schema.sql?rev=1.8
"""
from difflib import unified_diff

from pyrseas.testutils import DbMigrateTestCase


class PagilaTestCase(DbMigrateTestCase):

    def setUp(self):
        super(DbMigrateTestCase, self).setUp()
        self.add_public_schema(self.srcdb)
        self.add_public_schema(self.db)

    @classmethod
    def tearDown(cls):
        cls.remove_tempfiles('pagila')
        cls.remove_tempfiles('empty')

    def test_pagila(self):
        if self.db.version < 90600:
            self.skipTest('Only available on PG 9.6 and later')
        # Create the source schema
        self.execute_script(__file__, 'pagila-schema.sql')

        # Run pg_dump against source database
        srcdump = self.tempfile_path('pagila-src.dump')
        self.run_pg_dump(srcdump, True)

        # Create source YAML file
        srcyaml = self.tempfile_path('pagila-src.yaml')
        self.create_yaml(srcyaml, True)

        # Run pg_dump/dbtoyaml against empty target database
        emptydump = self.tempfile_path('empty.dump')
        self.run_pg_dump(emptydump)
        emptyyaml = self.tempfile_path('empty.yaml')
        self.create_yaml(emptyyaml)

        # Migrate the target database
        targsql = self.tempfile_path('pagila.sql')
        self.migrate_target(srcyaml, targsql)

        # Run pg_dump against target database
        targdump = self.tempfile_path('pagila.dump')
        self.run_pg_dump(targdump)

        # Create target YAML file
        targyaml = self.tempfile_path('pagila.yaml')
        self.create_yaml(targyaml)

        # diff pagila-src.dump against pagila.dump
        # order of triggers requires special handling
        adds = []
        subs = []
        for line in unified_diff(self.lines(srcdump), self.lines(targdump)):
            if line == '--- \n' or line == '+++ \n' or line.startswith('@@'):
                continue
            if line[:1] == '+':
                adds.append(line[1:-1])
            elif line[:1] == '-':
                subs.append(line[1:-1])
        subs = sorted(subs)
        for i, line in enumerate(sorted(adds)):
            assert line == subs[i]
        # diff pagila-src.yaml against pagila.yaml
        assert self.lines(srcyaml) == self.lines(targyaml)

        # Undo the changes
        self.migrate_target(emptyyaml, targsql)

        # Workaround problem with privileges on schema public
        self.db.execute("GRANT ALL ON SCHEMA public TO postgres")
        self.db.conn.commit()
        # Run pg_dump against target database
        self.run_pg_dump(targdump)

        self.db.execute("REVOKE ALL ON SCHEMA public FROM postgres")
        self.db.conn.commit()
        # Create target YAML file
        self.create_yaml(targyaml)

        # diff empty.dump against pagila.dump
        assert self.lines(emptydump) == self.lines(targdump)
        # diff empty.yaml against pagila.yaml
        assert self.lines(emptyyaml) == self.lines(targyaml)
