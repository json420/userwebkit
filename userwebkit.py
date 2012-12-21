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
`userwebkit` - so WebKitGtk apps can to talk to a `usercouch`.
"""

import sys
from os import path
from urllib.parse import urlparse, parse_qsl
import json
import optparse
import logging

import microfiber
from microfiber import _oauth_header, _basic_auth_header
import dbus
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GObject, Gtk, WebKit
from gi.repository.GObject import TYPE_PYOBJECT


__version__ = '13.01.0'
APPS = '/usr/share/couchdb/apps/'
GObject.threads_init()
DBusGMainLoop(set_as_default=True)
log = logging.getLogger('userwebkit')


def handler(d):
    assert path.abspath(d) == d
    return 	'{{couch_httpd_misc_handlers, handle_utils_dir_req, {}}}'.format(
        json.dumps(d)
    )


class CouchView(WebKit.WebView):
    __gsignals__ = {
        'open': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE,
            [TYPE_PYOBJECT]
        ),
    }

    def __init__(self, env=None, dmedia_resolver=None):
        super().__init__()
        self._logging_enabled = False
        self.connect('resource-request-starting', self._on_request)
        self.connect('navigation-policy-decision-requested',
            self._on_nav_policy_decision
        )
        self.set_env(env)
        self._dmedia_resolver = dmedia_resolver

    def set_env(self, env):
        self._env = env
        if env is None:
            self._u = None
            self._oauth = None
            self._basic = None
            return
        self._u = urlparse(env['url'])
        self._oauth = env.get('oauth')
        self._basic = env.get('basic')

    def enable_logging(self):
        if not self._logging_enabled:
            self._logging_enabled = True
            self.connect('console-message', self._on_console_message)

    def _on_console_message(self, view, message, line, source_id):
        log.debug('%s @%s: %s', source_id, line, message)

    def _on_request(self, view, frame, resource, request, response):
        if self._env is None:
            return
        uri = request.get_uri()
        message = request.get_message()
        if uri.startswith('dmedia'):
            if self._dmedia_resolver is None:
                request.set_uri('')
            else:
                request.set_uri(self._dmedia_resolver(uri))
            return
        u = urlparse(uri)
        if u.netloc != self._u.netloc:
            return
        if u.scheme != self._u.scheme:
            return
        if self._oauth:
            query = dict(parse_qsl(u.query))
            if u.query and not query:
                query = {u.query: ''}
            baseurl = ''.join([u.scheme, '://', u.netloc, u.path])
            method = message.method
            h = _oauth_header(self._oauth, method, baseurl, query)
        elif self._basic:
            h = _basic_auth_header(self._basic)
        else:
            return
        for (key, value) in h.items():
            message.request_headers.append(key, value)

    def _on_nav_policy_decision(self, view, frame, request, nav, policy):
        """
        Handle user trying to Navigate away from current page.

        Note that this will be called before `CouchView._on_resource_request()`.

        The *policy* arg is a ``WebPolicyDecision`` instance.  To handle the
        decision, call one of:

            * ``WebPolicyDecision.ignore()``
            * ``WebPolicyDecision.use()``
            * ``WebPolicyDecision.download()``

        And then return ``True``.

        Otherwise, return ``False`` or ``None`` to have the WebKit default
        behavior apply.
        """
        if self._env is None:
            return
        uri = request.get_uri()
        u = urlparse(uri)
        if u.netloc == self._u.netloc or u.scheme == 'file':
            return False
        if u.scheme in ('http', 'https'):
            self.emit('open', uri)
        policy.ignore()
        return True


class Inspector(Gtk.VBox):
    def __init__(self, env):
        super().__init__()

        hbox = Gtk.HBox()
        self.pack_start(hbox, False, False, 0)

        close = Gtk.Button(stock=Gtk.STOCK_CLOSE)
        hbox.pack_start(close, False, False, 2)
        close.connect('clicked', self.on_close)

        self.reload = Gtk.Button('Reload')
        hbox.pack_start(self.reload, False, False, 2)

        self.futon = Gtk.Button('CouchDB Futon')
        hbox.pack_start(self.futon, False, False, 2)

        scroll = Gtk.ScrolledWindow()
        self.pack_start(scroll, True, True, 0)
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)

        self.view = CouchView(env)
        scroll.add(self.view)

    def on_close(self, button):
        self.destroy()


class Hub(GObject.GObject):
    def __init__(self, view):
        super().__init__()
        self._view = view
        view.connect('notify::title', self._on_notify_title)

    def _on_notify_title(self, view, notify):
        title = view.get_property('title')
        if title is None:
            return
        try:
            obj = json.loads(title)
        except ValueError:
            return
        if not isinstance(obj, dict):
            return
        self.emit(obj['signal'], *obj['args'])

    def send(self, signal, *args):
        """
        Emit a signal by calling the JavaScript Signal.recv() function.
        """
        script = 'Hub.recv({!r})'.format(
            json.dumps({'signal': signal, 'args': args}, sort_keys=True)
        )
        self._view.execute_script(script)
        self.emit(signal, *args)        


def iter_gsignals(signals):
    assert isinstance(signals, dict)
    for (name, argnames) in signals.items():
        assert isinstance(argnames, list)
        args = [TYPE_PYOBJECT for argname in argnames]
        yield (name, (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, args))


def hub_factory(signals):
    if signals:
        class FactoryHub(Hub):
            __gsignals__ = dict(iter_gsignals(signals))
        return FactoryHub
    return Hub


class BaseApp(object):
    name = 'userwebkit'  # The namespace of your app, likely source package name
    dbname = 'userwebkit-0'  # Main CouchDB database name
    version = None  # Your app version, eg '12.04.0'
    title = 'App Window Title'  # Default Gtk.Window title
    page = 'index.html'  # Default page to load once CouchDB is available

    enable_inspector = True  # If True, enable WebKit inspector
    enable_logging = True  # If True, send console message to Python logging

    dmedia_resolver = None  # Callback to resolve Dmedia URIs

    proxy_bus = 'org.freedesktop.DC3'  # Dbus service that will start CouchDB
    proxy_path = '/'

    width = 960  # Default Gtk.Window width
    height = 540  # Default Gtk.Window height
    maximize = False  # If True, start with Gtk.Window maximized
    center = True  # If True, center the Gtk.Window within the screen
    decorated = True  # If False, call window.set_decorated(False)

    signals = None

    # Methods that subclasses likely want to override, in order they're called:
    def extend_parser(self, parser):
        """
        Called from BaseApp.parse().
        """
        pass

    def connect_hub_signals(self, hub):
        """
        Called from BaseApp.run(), after BaseApp.build_window().
        """
        pass

    def post_env_init(self):
        """
        Called from BaseApp.on_proxy(), right after BaseApp.set_env().
        """
        pass

    def choose_starting_page(self):
        """
        Called from BaseApp.get_page(), which is called from BaseApp.on_proxy().
        """
        return self.page

    def post_page_init(self, page):
        pass

    def __init__(self):
        self.env = None
        self.inspector = None

        # Figure out if we're running in-tree or not        
        script = path.abspath(sys.argv[0])
        tree = path.dirname(script)
        setup = path.join(tree, 'setup.py')
        ui = path.join(tree, 'ui')
        self.intree = (path.isfile(setup) and path.isdir(ui))
        self.ui = (ui if self.intree else path.join(APPS, self.name))

    def parse(self):
        parser = optparse.OptionParser(
            version=self.version,
        )
        parser.add_option('--benchmark',
            help='benchmark app startup time',
            action='store_true',
            default=False,
        )
        parser.add_option('--page',
            help='force UI to load specific HTML5 page, eg "foo.html"',
        )
        self.extend_parser(parser)
        (self.options, self.args) = parser.parse_args()

    def build_window(self):
        self.window = Gtk.Window()
        self.window.connect('destroy', self.quit)
        if self.maximize:
            self.window.maximize()
        if self.center:
            self.window.set_position(Gtk.WindowPosition.CENTER)
        if not self.decorated:
            self.window.set_decorated(False)
        self.window.set_default_size(self.width, self.height)
        self.window.set_title(self.title)
        self.vpaned = Gtk.VPaned()
        self.window.add(self.vpaned)
        self.scroll = Gtk.ScrolledWindow()
        self.vpaned.pack1(self.scroll, True, True)
        self.scroll.set_policy(
            Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC
        )

    def get_page(self):
        if self.options.page:
            return self.options.page
        return self.choose_starting_page()

    def run(self):
        self.parse()
        self.build_window()
        self.window.show_all()
        GObject.idle_add(self.on_idle)
        Gtk.main()

    def quit(self, *arg):
        # FIXME: This is a work-around for the segfault we're getting when
        # The window is destroyed before the inspector is
        if self.inspector:
            self.inspector.destroy()
        Gtk.main_quit()

    def on_idle(self):
        if self.options.benchmark:
            Gtk.main_quit()
            return
        session = dbus.SessionBus()
        self.proxy = session.get_object(self.proxy_bus, self.proxy_path)
        env = json.loads(self.proxy.GetEnv())

        # Add the CouchView
        self.view = CouchView(None, self.dmedia_resolver)
        self.view.connect('open', self.on_open)
        self.scroll.add(self.view)
        if self.enable_inspector:
            self.view.get_settings().set_property('enable-developer-extras', True)
            inspector = self.view.get_inspector()
            inspector.connect('inspect-web-view', self.on_inspect)
        if self.enable_logging:
            self.view.enable_logging()
        self.view.show()

        # Create the hub
        self.hub = hub_factory(self.signals)(self.view)
        self.connect_hub_signals(self.hub)
        
        self.set_env(env)
        self.post_env_init()
        page = self.get_page()
        self.load_page(page)
        self.post_page_init(page)

    def set_env(self, env):    
        self.env = env
        self.server = microfiber.Server(env)
        self.db = microfiber.Database(self.dbname, env) 
        self.db.ensure()
        if self.intree:
            self.server.put(
                handler(self.ui), '_config', 'httpd_global_handlers', '_intree'
            )
        self.view.set_env(env)
        if self.inspector is not None:
            self.inspector.view.set_env(env)

    def get_path(self, page):
        """
        Get absolute HTTP path of *page*.

        This method takes into account whether the app is running in-tree.

        For example, when running your app from the installed package:

        >>> app = BaseApp()
        >>> app.name = 'foo'
        >>> app.intree = False
        >>> app.get_path('bar.html')
        '/_apps/foo/bar.html'

        Or when running your app from inside the source tree:

        >>> app.intree = True
        >>> app.get_path('bar.html')
        '/_intree/bar.html'
        
        Lastly, if *page* is already an absolute HTTP path, it is returned
        unchanged:
        
        >>> app.get_path('/_utils/')
        '/_utils/'

        """
        if page.startswith('/'):
            return page
        if self.intree:
            return '/_intree/' + page
        return '/'.join(['/_apps', self.name, page])

    def load_page(self, page):
        self.view.load_uri(self.server._full_url(self.get_path(page)))

    def on_inspect(self, *args):
        self.inspector = Inspector(self.env)
        pos = self.window.get_allocated_height() * 2 // 3
        self.vpaned.set_position(pos)
        self.vpaned.pack2(self.inspector, True, True)
        self.inspector.show_all()
        self.inspector.reload.connect('clicked', self.on_reload)
        self.inspector.futon.connect('clicked', self.on_futon)
        return self.inspector.view

    def on_reload(self, button):
        self.view.reload_bypass_cache()

    def on_futon(self, button):
        self.load_page('/_utils/')

    def on_open(self, view, uri):
        import subprocess
        subprocess.check_call(['/usr/bin/xdg-open', uri])


