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
from base64 import b32encode
from urllib.parse import urlparse
from random import SystemRandom
from urllib.parse import urlparse

from microfiber import random_id

import userwebkit


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
    def __init__(self, uri):
        self.__uri = uri
        self._set_uri = None

    def get_uri(self):
        return self.__uri

    def set_uri(self, uri):
        assert self._set_uri is None
        self._set_uri = uri


class DummyPolicy:
    def __init__(self):
        self._called = False

    def ignore(self):
        assert self._called is False
        self._called = True


class DummyResolver:
    def __init__(self):
        self._calls = []

    def __call__(self, uri):
        self._calls.append(uri)
        u = urlparse(uri)
        assert u.scheme == 'dmedia'
        _id = u.path
        assert len(_id) == 48
        return '/'.join(['/home/.dmedia/files', _id[:2], _id[2:]])



class TestCouchView(TestCase):
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

    def testset_env(self):
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
            '/'.join(['/home/.dmedia/files', id1[:2], id1[2:]])
        )
        self.assertEqual(resolver._calls, [uri1])
        
        # Lets try one more:
        id2 = random_id(30)
        uri2 = 'dmedia:' + id2
        request = DummyRequest(uri2)
        self.assertIsNone(view._on_request(None, None, None, request, None))
        self.assertEqual(
            request._set_uri,
            '/'.join(['/home/.dmedia/files', id2[:2], id2[2:]])
        )
        self.assertEqual(resolver._calls, [uri1, uri2])

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

