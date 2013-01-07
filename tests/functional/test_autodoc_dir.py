# -*- coding: utf-8 -*-
"""Test dbtoyaml and yamltodb using autodoc schema but I/O to/from a directory

Same as test_autodoc.py but with directory tree instead of a single YAML file.
See http://cvs.pgfoundry.org/cgi-bin/cvsweb.cgi/~checkout~/autodoc/autodoc/
regressdatabase.sql?rev=1.2
"""
import unittest

from pyrseas.testutils import DbMigrateTestCase


class AutodocTestCase(DbMigrateTestCase):

    @classmethod
    def tearDownClass(cls):
        cls.remove_tempfiles('autodoc')
        cls.remove_tempfiles('empty')

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
        srcdir = self.tempfile_path('autodoc')
        self.create_yaml_dir(srcdir, True)

        # Run pg_dump/dbtoyaml against empty target database
        emptydump = self.tempfile_path('empty.dump')
        self.run_pg_dump(emptydump)
        emptyyaml = self.tempfile_path('empty.yaml')
        self.create_yaml(emptyyaml)
        emptydir = self.tempfile_path('empty')
        self.create_yaml_dir(emptydir)

        # Migrate the target database
        targsql = self.tempfile_path('autodoc.sql')
        self.migrate_target_dir(srcdir, targsql)

        # Run pg_dump against target database
        targdump = self.tempfile_path('autodoc.dump')
        self.run_pg_dump(targdump)

        # Create target YAML file
        targyaml = self.tempfile_path('autodoc.yaml')
        self.create_yaml(targyaml)

        # diff autodoc-src.dump against autodoc.dump
        self.assertEqual(self.lines(srcdump), self.lines(targdump))
        # diff autodoc-src.yaml against autodoc.yaml
        self.assertEqual(self.lines(srcyaml), self.lines(targyaml))

        # Undo the changes
        self.migrate_target_dir(emptydir, targsql)

        # Run pg_dump against target database
        self.run_pg_dump(targdump)

        # Create target YAML file
        self.create_yaml(targyaml)

        # diff empty.dump against autodoc.dump
        self.assertEqual(self.lines(emptydump), self.lines(targdump))
        # diff empty.yaml against autodoc.yaml
        self.assertEqual(self.lines(emptyyaml), self.lines(targyaml))


def suite():
    tests = unittest.TestLoader().loadTestsFromTestCase(AutodocTestCase)
    return tests

if __name__ == '__main__':
    unittest.main(defaultTest='suite')
