#!/usr/bin/python3

# novacut: the collaborative video editor
# Copyright (C) 2011 Novacut Inc
#
# This file is part of `novacut`.
#
# `novacut` is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option)
# any later version.
#
# `novacut` is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for
# more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with `novacut`.  If not, see <http://www.gnu.org/licenses/>.
#
# Authors:
#   Jason Gerard DeRose <jderose@novacut.com>

import optparse

from userwebkit import BaseUI


class UI(BaseUI):
    app = 'demo'
    page = 'index.html'
    splash = 'splash.html'
    title = 'Demo'
    databases = ['demo']


parser = optparse.OptionParser()
parser.add_option('--benchmark',
    help='benchmark app startup time',
    action='store_true',
    default=False,
)
(options, args) = parser.parse_args()


ui = UI(options.benchmark)

def on_title_data(view, obj):
    print(obj)
    ui.window.set_title(str(obj))

ui.view.connect('title_data', on_title_data)
ui.run()
