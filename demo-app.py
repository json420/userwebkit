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

    page = 'index.html'

    proxy_bus = 'org.freedesktop.Dmedia'
    local = None
    #decorated = False

    signals = {
        'toggle': ['active'],
        'timer': ['count'],
        'echo': ['count_times_two'],
    }

    # Method overrides, in the order they get called:
    def extend_parser(self, parser):
        print('App.extend_parser(<OptionParser>)')
        parser.add_option('--demo',
            help='A fun option added by overriding BaseApp.extend_parser()',
        )

    def connect_hub_signals(self, hub):
        print('App.connect_hub_signals(<Hub>)')
        hub.connect('echo', self.on_echo)
        hub.connect('toggle', self.on_toggle)

        # Good a place as any to do this:
        self.count = 0
        self.timer = Timer(1, self.on_timer)

    def post_env_init(self):
        print('App.post_env_init()')

    def choose_starting_page(self):
        print('App.choose_starting_page()')
        return self.page

    def post_page_init(self, page):
        print('App.post_page_init({!r})'.format(page))

    def on_echo(self, hub, count_times_two):
        self.window.set_title('echo: {}'.format(count_times_two))

    def on_toggle(self, hub, active):
        if active:
            self.timer.start()
        else:
            self.timer.stop() 

    def on_timer(self):
        self.hub.send('timer', self.count)
        self.count += 1  

    def dmedia_resolver(self, uri):
        if self.env is None:
            return ''
        if self.local is None:
            self.local = local.LocalSlave(self.env)
        try:
            u = urlparse(uri)
            _id = u.path
            doc = self.local.get_doc(_id)
            if doc.get('proxies'):
                proxies = doc['proxies']
                for proxy in proxies:
                    try:
                        st = self.local.stat(proxy)
                        return 'file://' + st.name
                    except (local.NoSuchFile, local.FileNotLocal):
                        pass
            st = self.local.stat2(doc)
            return 'file://' + st.name
        except Exception:    
            return ''


app = App()
app.run()

