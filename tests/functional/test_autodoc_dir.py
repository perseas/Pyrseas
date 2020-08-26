# -*- coding: utf-8 -*-
"""Test dbtoyaml and yamltodb using autodoc schema but I/O to/from a directory

Same as test_autodoc.py but with directory tree instead of a single YAML file.
See http://cvs.pgfoundry.org/cgi-bin/cvsweb.cgi/~checkout~/autodoc/autodoc/
regressdatabase.sql?rev=1.2
"""
from pyrseas.testutils import DbMigrateTestCase


class AutodocTestCase(DbMigrateTestCase):

    def setUp(self):
        super(DbMigrateTestCase, self).setUp()
        self.add_public_schema(self.srcdb)
        self.add_public_schema(self.db)
        self.remove_tempfiles('metadata')

    @classmethod
    def tearDown(cls):
        cls.remove_tempfiles('autodoc')
        cls.remove_tempfiles('metadata')

    def test_autodoc(self):
        # Create the source schema
        self.execute_script(__file__, 'autodoc-schema.sql')

        # Run pg_dump against source database
        srcdump = self.tempfile_path('autodoc-src.dump')
        self.run_pg_dump(srcdump, True)

        # Create source YAML file and directory tree
        # Note: the single YAML file is for verification against the target,
        #       the YAML directory tree is for processing
        srcyaml = self.tempfile_path('autodoc-src.yaml')
        self.create_yaml(srcyaml, True)
        self.create_yaml(None, True)

        # Migrate the target database
        targsql = self.tempfile_path('autodoc.sql')
        self.migrate_target(None, targsql)

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
        self.srcdb.execute_commit(
            "DROP SCHEMA inherit, product, store, warehouse CASCADE")
        # Create source YAML file and directory tree
        srcyaml = self.tempfile_path('autodoc-src-empty.yaml')
        self.create_yaml(srcyaml, True)
        self.create_yaml(None, True)
        targsql = self.tempfile_path('autodoc-empty.sql')
        self.migrate_target(None, targsql)

        # Run pg_dump against source database
        srcdump = self.tempfile_path('autodoc-src-empty.dump')
        self.run_pg_dump(srcdump, True)

        # Run pg_dump against target database
        targdump = self.tempfile_path('autodoc-empty.dump')
        self.run_pg_dump(targdump)

        # Create target YAML file
        targyaml = self.tempfile_path('autodoc-empty.yaml')
        self.create_yaml(targyaml)

        # diff empty.dump against autodoc.dump
        assert self.lines(srcdump) == self.lines(targdump)
        # diff empty.yaml against autodoc.yaml
        assert self.lines(srcyaml) == self.lines(targyaml)
