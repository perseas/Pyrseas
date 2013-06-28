# -*- coding: utf-8 -*-
"""Test configuration files"""

from pyrseas.config import Config


def test_defaults():
    "Create a configuration with defaults"
    cfg = Config()
    for key in ['audit_columns', 'functions', 'func_templates', 'columns',
                'triggers']:
        assert key in cfg['augmenter']
