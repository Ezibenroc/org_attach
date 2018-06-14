#!/usr/bin/env python3

import sys
import os
import re
from subprocess import Popen, PIPE
from setuptools import setup

if __name__ == '__main__':
    version = re.search(
        "^__version__\s*=\s*'(.*)'",
        open('org_attach/version.py').read(),
        re.M).group(1)
    setup(
        name='org_attach',
        packages=['org_attach'],
        entry_points={
            'console_scripts': ['org_attach = org_attach.org_attach:main']
        },
        version=version,
        description='Script to attach various types of files to an org-mode notebook.',
        author="Tom Cornebize",
        author_email="tom.cornebize@gmail.com",
        url='https://github.com/Ezibenroc/DOI_to_org',
        install_requires=[
            'pybtex',
            'python-magic',
            'requests',
            'jupyter',
        ],
    )
