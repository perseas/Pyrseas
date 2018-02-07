# -*- coding: utf-8 -*-
"""Test dbtoyaml and yamltodb using autodoc schema

See http://cvs.pgfoundry.org/cgi-bin/cvsweb.cgi/~checkout~/autodoc/autodoc/
regressdatabase.sql?rev=1.2
"""
from pyrseas.testutils import DbMigrateTestCase


class AutodocTestCase(DbMigrateTestCase):

    def setUp(self):
        super(DbMigrateTestCase, self).setUp()
        self.add_public_schema(self.srcdb)
        self.add_public_schema(self.db)

    @classmethod
    def tearDown(cls):
        cls.remove_tempfiles('autodoc')
        cls.remove_tempfiles('empty')

    def test_autodoc(self):
        # Create the source schema
        self.execute_script(__file__, 'autodoc-schema.sql')

        # Run pg_dump against source database
        srcdump = self.tempfile_path('autodoc-src.dump')
        self.run_pg_dump(srcdump, True)

        # Create source YAML file
        srcyaml = self.tempfile_path('autodoc-src.yaml')
        self.create_yaml(srcyaml, True)

        # Run pg_dump/dbtoyaml against empty target database
        emptydump = self.tempfile_path('empty.dump')
        self.run_pg_dump(emptydump)
        emptyyaml = self.tempfile_path('empty.yaml')
        self.create_yaml(emptyyaml)

        # Migrate the target database
        targsql = self.tempfile_path('autodoc.sql')
        self.migrate_target(srcyaml, targsql)

        # Run pg_dump against target database
        targdump = self.tempfile_path('autodoc.dump')
        self.run_pg_dump(targdump)

        # Create target YAML file
        targyaml = self.tempfile_path('autodoc.yaml')
        self.create_yaml(targyaml)

        # diff autodoc-src.dump against autodoc.dump
        assert self.lines(srcdump) == self.lines(targdump)
        # diff autodoc-src.yaml against autodoc.yaml
        assert self.lines(srcyaml) == self.lines(targyaml)

        # Undo the changes
        self.migrate_target(emptyyaml, targsql)

        # Run pg_dump against target database
        self.run_pg_dump(targdump)

        # Create target YAML file
        self.create_yaml(targyaml)

        # diff empty.dump against autodoc.dump
        assert self.lines(emptydump) == self.lines(targdump)
        # diff empty.yaml against autodoc.yaml
        assert self.lines(emptyyaml) == self.lines(targyaml)
