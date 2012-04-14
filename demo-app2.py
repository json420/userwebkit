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

from urllib.parse import urlparse

from dmedia import local
from dmedia.gtk.util import Timer

import userwebkit
from userwebkit import BaseApp


class App(BaseApp):
    name = 'demo'
    dbname = 'demo-0'
    version = userwebkit.__version__
    title = 'UserWebKit Demo'

    #splash = 'splash.html'
    page = 'index2.html'
    proxy_bus = 'org.freedesktop.Dmedia'


app = App()
app.run()

