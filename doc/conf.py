import os
import sys

sys.path.insert(0,
                os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.todo',
    'sphinx.ext.viewcode',
]

autodoc_default_flags = ['members', 'show-inheritance', 'inherited-members']
autodoc_member_order = 'bysource'

source_suffix = '.rst'

master_doc = 'index'

project = 'StackLight Integration Tests'
copyright = 'Copyright 2016 Mirantis, Inc.' \
            'Licensed under the Apache License, Version 2.0' \
            ' (the "License"); you may not use this file except in' \
            ' compliance with the License. You may obtain a copy' \
            ' of the License at http://www.apache.org/licenses/LICENSE-2.0'

exclude_patterns = ['_build']

pygments_style = 'sphinx'

html_theme = 'default'
htmlhelp_basename = 'StackLightintegrationtestsdoc'

intersphinx_mapping = {'http://docs.python.org/': None}
