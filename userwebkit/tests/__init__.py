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
Unit tests for `userwebkit`.
"""

from unittest import TestCase
import os
from os import path
from base64 import b32encode
from urllib.parse import urlparse
from random import SystemRandom

import microfiber
from microfiber import random_id
from usercouch.misc import CouchTestCase
from gi.repository.GObject import SIGNAL_RUN_LAST, TYPE_NONE, TYPE_PYOBJECT

import userwebkit


orig_log = userwebkit.log
random = SystemRandom()


def random_key():
    return b32encode(os.urandom(10)).decode('ascii')


def random_oauth():
    return dict(
        (k, random_key())
        for k in ('consumer_key', 'consumer_secret', 'token', 'token_secret')
    )


def random_basic():
    return dict(
        (k, random_key())
        for k in ('username', 'password')
    )


def random_env():
    port = random.randint(2000, 50000)
    return {
        'port': port,
        'url': 'http://localhost:{}/'.format(port),
        'oauth': random_oauth(),
        'basic': random_basic(),
    }


class DummyCallback:
    def __init__(self):
        self._calls = []

    def __call__(self, *args):
        self._calls.append(args)


class DummyRequest:
    def __init__(self, uri, message = None):
        self.__uri = uri
        self._set_uri = None
        self.__message = message

    def get_uri(self):
        return self.__uri

    def set_uri(self, uri):
        assert self._set_uri is None
        self._set_uri = uri

    def get_message(self):
        return self.__message

class DummyPolicy:
    def __init__(self):
        self._called = False

    def ignore(self):
        assert self._called is False
        self._called = True


class DummyResolver:
    def __init__(self):
        self._calls = []

    def __call__(self, _id):
        self._calls.append(_id)
        assert len(_id) == 48
        filename = path.join('/home/.dmedia/files', _id[:2], _id[2:])
        return (_id, 0, filename)


class DummyCouchView:
    def __init__(self):
        self._scripts = []

    def set_env(self, env):
        assert not hasattr(self, '_env')
        self._env = env

    def connect(self, *args):
        assert not hasattr(self, '_connect')
        self._connect = args

    def execute_script(self, script):
        self._scripts.append(script)
 

class DummyLogger:
    def __init__(self):
        self._messages = []

    def debug(self, *args):
        self._messages.append(args)


class TestConstants(TestCase):
    def test_version(self):
        self.assertIsInstance(userwebkit.__version__, str)
        (year, month, rev) = userwebkit.__version__.split('.')
        y = int(year)
        self.assertTrue(y >= 13)
        self.assertEqual(str(y), year)
        m = int(month)
        self.assertTrue(1 <= m <= 12)
        self.assertEqual('{:02d}'.format(m), month)
        r = int(rev)
        self.assertTrue(r >= 0)
        self.assertEqual(str(r), rev)


class TestFunctions(TestCase):
    def test_iter_gsignals(self):
        self.assertEqual(
            dict(userwebkit.iter_gsignals({})), 
            {}
        )
        signals = {
            'foo': [],
            'bar': ['one'],
            'baz': ['one', 'two'],
        }
        gsignals = {
            'foo': (SIGNAL_RUN_LAST, TYPE_NONE, []),
            'bar': (SIGNAL_RUN_LAST, TYPE_NONE, [TYPE_PYOBJECT]),
            'baz': (SIGNAL_RUN_LAST, TYPE_NONE, [TYPE_PYOBJECT, TYPE_PYOBJECT]),
        }
        self.assertEqual(
            dict(userwebkit.iter_gsignals(signals)), 
            gsignals
        )

    def test_hub_factory(self):
        self.assertIs(userwebkit.hub_factory(None), userwebkit.Hub)
        self.assertIs(userwebkit.hub_factory({}), userwebkit.Hub)
        signals = {
            'foo': [],
            'bar': ['one'],
            'baz': ['one', 'two'],
        }
        klass = userwebkit.hub_factory(signals)
        self.assertIsNot(klass, userwebkit.Hub)
        self.assertTrue(issubclass(klass, userwebkit.Hub))
        self.assertEqual(klass.__name__, 'FactoryHub')

        # Make sure we can connect to all the expected signals:
        view = DummyCouchView()
        hub = klass(view)
        self.assertEqual(view._connect,
            ('notify::title', hub._on_notify_title)
        )
        cb = DummyCallback()
        hub.connect('foo', cb)
        hub.connect('bar', cb)
        hub.connect('baz', cb)
        self.assertEqual(cb._calls, [])
        self.assertEqual(view._scripts, [])
 
        # Now test signal emit/send:
        hub.send('foo')
        hub.send('bar', 17)
        hub.send('baz', True, None)
        self.assertEqual(cb._calls,
            [
                (hub,),
                (hub, 17),
                (hub, True, None),
            ]   
        )
        self.assertEqual(view._scripts,
            [
                'Hub.recv(\'{"args": [], "signal": "foo"}\')',
                'Hub.recv(\'{"args": [17], "signal": "bar"}\')',
                'Hub.recv(\'{"args": [true, null], "signal": "baz"}\')',
            ]
        )


class TestCouchView(TestCase):
    def tearDown(self):
        userwebkit.log = orig_log

    def test_init(self):
        view = userwebkit.CouchView()
        self.assertIsNone(view._env)
        self.assertIsNone(view._u)
        self.assertIsNone(view._oauth)
        self.assertIsNone(view._basic)

        view = userwebkit.CouchView(None)
        self.assertIsNone(view._env)
        self.assertIsNone(view._u)
        self.assertIsNone(view._oauth)
        self.assertIsNone(view._basic)

        env = random_env()
        view = userwebkit.CouchView(env)
        self.assertIs(view._env, env)
        self.assertEqual(view._u, urlparse(env['url']))
        self.assertEqual(view._oauth, env['oauth'])
        self.assertEqual(view._basic, env['basic'])

    def test_set_env(self):
        view = userwebkit.CouchView()

        env = random_env()
        self.assertIsNone(view.set_env(env))
        self.assertIs(view._env, env)
        self.assertEqual(view._u, urlparse(env['url']))
        self.assertEqual(view._oauth, env['oauth'])
        self.assertEqual(view._basic, env['basic'])

        env = random_env()
        del env['oauth']
        del env['basic']
        self.assertIsNone(view.set_env(env))
        self.assertIs(view._env, env)
        self.assertEqual(view._u, urlparse(env['url']))
        self.assertIsNone(view._oauth)
        self.assertIsNone(view._basic)

        self.assertIsNone(view.set_env(None))
        self.assertIsNone(view._env)
        self.assertIsNone(view._u)
        self.assertIsNone(view._oauth)
        self.assertIsNone(view._basic)

    def test_enable_logging(self):
        view = userwebkit.CouchView()
        self.assertFalse(view._logging_enabled)
        self.assertIsNone(view.enable_logging())
        self.assertTrue(view._logging_enabled)
        self.assertIsNone(view.enable_logging())

    def test_on_console_message(self):
        view = userwebkit.CouchView()
        log = DummyLogger()
        userwebkit.log = log
        message = 'hello ' + random_id()
        line = 25
        source_id = 'http://localhost:36163/_intree/index.html'
        view._on_console_message(None, message, line, source_id)
        self.assertEqual(
            log._messages,
            [('%s @%s: %s', source_id, line, message)]
        )

    def test_on_request(self):
        view = userwebkit.CouchView()
        self.assertIsNone(view._env)

        # Make sure on_request() immediately returns when env is None:
        self.assertIsNone(view._on_request(None, None, None, None, None))

        # Test with dmedia: URI when dmedia_resolver is None:
        env = random_env()
        view.set_env(env)
        _id = random_id(30)
        uri = 'dmedia:' + _id
        request = DummyRequest(uri)
        self.assertIsNone(view._on_request(None, None, None, request, None))
        self.assertEqual(request._set_uri, '')

        # Test with dmedia: URI when dmedia_resolver is callable:
        env = random_env()
        resolver = DummyResolver()
        view = userwebkit.CouchView(env, resolver)
        self.assertIs(view._dmedia_resolver, resolver)
        id1 = random_id(30)
        uri1 = 'dmedia:' + id1
        request = DummyRequest(uri1)
        self.assertIsNone(view._on_request(None, None, None, request, None))
        self.assertEqual(
            request._set_uri,
            '/'.join(['file:///home/.dmedia/files', id1[:2], id1[2:]])
        )
        self.assertEqual(resolver._calls, [id1])

        # Lets try one more:
        id2 = random_id(30)
        uri2 = 'dmedia:' + id2
        request = DummyRequest(uri2)
        self.assertIsNone(view._on_request(None, None, None, request, None))
        self.assertEqual(
            request._set_uri,
            '/'.join(['file:///home/.dmedia/files', id2[:2], id2[2:]])
        )
        self.assertEqual(resolver._calls, [id1, id2])

    def test_on_nav_policy_decision(self):
        callback = DummyCallback()
        view = userwebkit.CouchView()
        view.connect('open', callback)

        # Make sure on_request() immediately returns when env is None:
        self.assertIsNone(
            view._on_nav_policy_decision(None, None, None, None, None)
        )
        self.assertEqual(callback._calls, [])

        # When URI netloc env, should return False
        env = random_env()
        view.set_env(env)
        request = DummyRequest(env['url'] + 'foo')
        self.assertIs(
            view._on_nav_policy_decision(None, None, request, None, None),
            False
        )
        self.assertEqual(callback._calls, [])

        # When URI scheme is 'file', should return False (needed for Inspector)
        request = DummyRequest(
            'file:///usr/share/webkitgtk-3.0/webinspector/inspector.html'
        )
        self.assertIs(
            view._on_nav_policy_decision(None, None, request, None, None),
            False
        )
        self.assertEqual(callback._calls, [])

        # For external http, https URI, should fire 'open' signal, call
        # policy.ignore(), and return True
        request = DummyRequest('http://www.ubuntu.com/')
        policy = DummyPolicy()
        self.assertIs(
            view._on_nav_policy_decision(None, None, request, None, policy),
            True
        )
        self.assertIs(policy._called, True)
        self.assertEqual(callback._calls,
            [
                (view, 'http://www.ubuntu.com/'),   
            ]
        )
 
        request = DummyRequest('https://launchpad.net/novacut')
        policy = DummyPolicy()
        self.assertIs(
            view._on_nav_policy_decision(None, None, request, None, policy),
            True
        )
        self.assertIs(policy._called, True)
        self.assertEqual(callback._calls,
            [
                (view, 'http://www.ubuntu.com/'),
                (view, 'https://launchpad.net/novacut'),  
            ]
        )

        # For other non-internal URI, should just call policy.ignore() and
        # return True... should not fire 'open'
        request = DummyRequest('ftp://example.com/')
        policy = DummyPolicy()
        self.assertIs(
            view._on_nav_policy_decision(None, None, request, None, policy),
            True
        )
        self.assertIs(policy._called, True)
        self.assertEqual(callback._calls,
            [
                (view, 'http://www.ubuntu.com/'),
                (view, 'https://launchpad.net/novacut'),  
            ]
        )
        
        
class DummyOptions:
    def __init__(self, benchmark=False, page=None):
        self.benchmark = benchmark
        self.page = page


class DummyServer:
    def __init__(self, env):
        u = urlparse(env['url'])
        self.scheme = u.scheme
        self.netloc = u.netloc

    def _full_url(self, path):
        return ''.join([self.scheme, '://', self.netloc, path])


class TestBaseApp(TestCase):
    def test_init(self):
        app = userwebkit.BaseApp()
        self.assertIsNone(app.inspector)
        self.assertIsNone(app.env)
        self.assertIsInstance(app.intree, bool)
        self.assertTrue(path.isdir(app.ui))

        # Test all the default class attribute values:
        self.assertEqual(app.name, 'userwebkit')
        self.assertEqual(app.dbname, 'userwebkit-0')
        self.assertIsNone(app.version)
        self.assertEqual(app.title, 'App Window Title')
        self.assertEqual(app.page, 'index.html')

        self.assertIs(app.enable_inspector, True)

        self.assertIsNone(app.dmedia_resolver)

        self.assertEqual(app.proxy_bus, 'org.freedesktop.DC3')
        self.assertEqual(app.proxy_path, '/')

        self.assertEqual(app.width, 960)
        self.assertEqual(app.height, 540)
        self.assertIs(app.maximize, False)

    def test_get_page(self):
        inst = userwebkit.BaseApp()
        inst.options = DummyOptions()
        self.assertEqual(inst.get_page(), 'index.html')
        inst.options = DummyOptions(page='stuff.html')
        self.assertEqual(inst.get_page(), 'stuff.html')

        class UI(userwebkit.BaseApp):
            page = 'foo.html'

        inst = userwebkit.BaseApp()
        inst.options = DummyOptions()
        self.assertEqual(inst.get_page(), 'index.html')
        inst.options = DummyOptions(page='junk.html')
        self.assertEqual(inst.get_page(), 'junk.html')

    def test_get_path(self):
        app = userwebkit.BaseApp()

        # Test when in-tree:
        app.intree = True
        self.assertEqual(app.get_path('/_utils/'), '/_utils/')
        self.assertEqual(app.get_path('foo.html'), '/_intree/foo.html')

        # Test when not in-tree:
        app.intree = False
        self.assertEqual(app.get_path('/_utils/'), '/_utils/')
        self.assertEqual(app.get_path('foo.html'), '/_apps/userwebkit/foo.html')

        # Test when not in-tree and name has been overridden:
        app.name = 'supercool'
        self.assertEqual(app.get_path('/_utils/'), '/_utils/')
        self.assertEqual(app.get_path('foo.html'), '/_apps/supercool/foo.html')


class TestBaseAppLive(CouchTestCase):
    def test_set_env(self):
        app = userwebkit.BaseApp()
        app.view = DummyCouchView()
        self.assertIsNone(app.env)
        app.set_env(self.env)
        self.assertIs(app.env, self.env)
        self.assertIs(app.view._env, self.env)
        self.assertIsInstance(app.server, microfiber.Server)
        self.assertIsInstance(app.db, microfiber.Database)
        self.assertEqual(app.db.get()['db_name'], 'userwebkit-0')
        if app.intree:
            self.assertEqual(
                app.server.get('_config', 'httpd_global_handlers', '_intree'),
                userwebkit.handler(app.ui)
            )
        
        

