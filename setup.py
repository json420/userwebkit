#!/usr/bin/env python3

# userwebkit: so WebKitGtk apps can to talk to a usercouch
# Copyright (C) 2011 Novacut Inc
# 
# This file is part of `userwebkit`.
# 
# `userwebkit` is free software: you can redistribute it and/or modify it under
# the terms of the GNU Lesser General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
# 
# `userwebkit` is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Lesser General Public License for more
# details.
# 
# You should have received a copy of the GNU Lesser General Public License along
# with `userwebkit`.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#   Jason Gerard DeRose <jderose@novacut.com>

"""
Install `userwebkit`.
"""

import sys
if sys.version_info < (3, 4):
    sys.exit('ERROR: UserWebKit requires Python 3.4 or newer')

from distutils.core import setup
from distutils.cmd import Command
import os
from os import path


class Test(Command):
    description = 'run unit tests and doc tests'

    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        from userwebkit.tests.run import run_tests
        if not run_tests():
            raise SystemExit('2')


setup(
    name='userwebkit',
    description='so WebKitGtk apps can to talk to a usercouch',
    url='https://launchpad.net/userwebkit',
    version='14.10.0',
    author='Jason Gerard DeRose',
    author_email='jderose@novacut.com',
    license='LGPLv3+',
    packages=['userwebkit', 'userwebkit.tests'],
    cmdclass={'test': Test},
    data_files=[
        ('share/couchdb/apps/userwebkit',
            [path.join('ui', name) for name in os.listdir('ui')]
        ),
    ],
)

