
import asyncio
from importlib import import_module
from unittest.mock import AsyncMock, MagicMock

from channels.auth import AuthMiddleware
from channels.sessions import SessionMiddleware
from django.conf import settings
from django.test import RequestFactory, TestCase, Client, TransactionTestCase, override_settings
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User
from ccs.auth.middleware import ChannelsCookieSessionInjectorMiddleware, HeaderSessionMiddleware, SessionHeaderAuthenticationStack

class TestMiddleware (TestCase):
    def setUp(self):
        self.user = User.objects.create_user("user", password = "password")
        self.sudo = User.objects.create_superuser("sudo", password = "password")
        self.cli = Client()
        self.factory = RequestFactory()
        self.middlew = HeaderSessionMiddleware(lambda : None)
    def getSessionKey (self, user):
        self.cli = Client()
        return self.cli.get("/login/", data = { "username": user, "password": "password" }).json()['session_id']
    def test_no_session_key (self):
        request = self.factory.get( "/" )
        self.middlew.process_request(request)
        session = request.session
        self.assertIsNone(session.session_key)
    @override_settings(ROOT_URLCONF="ccs.urls")
    def test_with_invalid_session_key (self):
        session_key = self.getSessionKey("user") + 'K'
        request = self.factory.get("/", headers = { "X-Session-ID": session_key })
        self.middlew.process_request(request)
        session = request.session
        self.assertEqual(session.session_key, session_key)
        self.assertIsNone( session.get('_auth_user_id') )
    @override_settings(ROOT_URLCONF="ccs.urls")
    def test_simple_user (self):
        session_key = self.getSessionKey("user")
        request = self.factory.get("/", headers = { "X-Session-ID": session_key })
        self.middlew.process_request(request)
        session = request.session
        self.assertEqual(session.session_key, session_key)
        self.assertEqual(session.get('_auth_user_id'), str(self.user.pk))
    @override_settings(ROOT_URLCONF="ccs.urls")
    def test_sudo_user (self):
        session_key = self.getSessionKey("sudo")
        request = self.factory.get("/", headers = { "X-Session-ID": session_key })
        self.middlew.process_request(request)
        session = request.session
        self.assertEqual(session.session_key, session_key)
        self.assertEqual(session.get('_auth_user_id'), str(self.sudo.pk))

class TestCookieInjectionStack (TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user("user", password = "password")
        self.sudo = User.objects.create_superuser("sudo", password = "password")

        self.mock = AsyncMock()
        self.midd = SessionHeaderAuthenticationStack( self.mock )
    
    def run_scope (self, scope):
        async def U (*args, **kwargs): pass
        asyncio.run(self.midd(scope, U, U))

    def getSessionKey (self, user):
        self.cli = Client()
        return self.cli.get("/login/", data = { "username": user, "password": "password" }).json()['session_id']
    @override_settings(ROOT_URLCONF="ccs.urls")
    def test_anonymous (self):
        scope = { "headers": [] }
        self.run_scope(scope)
        scope = self.mock.call_args.args[0]
        assert scope["user"].pk is None
        del scope["session"]
        del scope["user"]
        self.assertEqual(scope, { "headers": [], "cookies": {} })
    @override_settings(ROOT_URLCONF="ccs.urls")
    def test_user (self):
        session = self.getSessionKey("user").encode()
        scope = { "headers": [ (b"x-session-id", session) ] }
        self.run_scope(scope)
        scope = self.mock.call_args.args[0]
        self.assertEqual(scope['headers'], [(b'x-session-id', session)])
        self.assertEqual(scope['cookies'], {'sessionid': session.decode()})
        self.assertEqual(scope['user'].username, "user")
        self.assertEqual(scope['user'].pk, self.user.pk)
    @override_settings(ROOT_URLCONF="ccs.urls")
    def test_sudo_and_cookies (self):
        session = self.getSessionKey("sudo").encode()
        scope = { "headers": [ (b"x-session-id", session), (b"cookie", b"user_pref=dark_mode") ] }
        self.run_scope(scope)
        scope = self.mock.call_args.args[0]
        self.assertEqual(scope['headers'], [(b'x-session-id', session), (b'cookie', b'user_pref=dark_mode')])
        self.assertEqual(scope['cookies'], {'sessionid': session.decode(), "user_pref": "dark_mode"})
        self.assertEqual(scope['user'].username, "sudo")
        self.assertEqual(scope['user'].pk, self.sudo.pk)


class TestCookieInjectionStack_NoCookieMiddleware (TransactionTestCase):
    def setUp(self):
        self.user = User.objects.create_user("user", password = "password")
        self.sudo = User.objects.create_superuser("sudo", password = "password")

        self.mock = AsyncMock()
        self.midd = ChannelsCookieSessionInjectorMiddleware(
            SessionMiddleware(AuthMiddleware(self.mock)))
    
    def run_scope (self, scope):
        async def U (*args, **kwargs): pass
        asyncio.run(self.midd(scope, U, U))

    def getSessionKey (self, user):
        self.cli = Client()
        return self.cli.get("/login/", data = { "username": user, "password": "password" }).json()['session_id']
    @override_settings(ROOT_URLCONF="ccs.urls")
    def test_anonymous (self):
        scope = { "headers": [] }
        self.run_scope(scope)
        scope = self.mock.call_args.args[0]
        assert scope["user"].pk is None
        del scope["session"]
        del scope["user"]
        self.assertEqual(scope, { "headers": [], "cookies": {} })
    @override_settings(ROOT_URLCONF="ccs.urls")
    def test_user (self):
        session = self.getSessionKey("user").encode()
        scope = { "headers": [ (b"x-session-id", session) ] }
        self.run_scope(scope)
        scope = self.mock.call_args.args[0]
        self.assertEqual(scope['headers'], [(b'x-session-id', session)])
        self.assertEqual(scope['cookies'], {'sessionid': session.decode()})
        self.assertEqual(scope['user'].username, "user")
        self.assertEqual(scope['user'].pk, self.user.pk)
    @override_settings(ROOT_URLCONF="ccs.urls")
    def test_sudo_and_cookies (self):
        session = self.getSessionKey("sudo").encode()
        scope = { "headers": [ (b"x-session-id", session), (b"cookie", b"user_pref=dark_mode") ] }
        self.run_scope(scope)
        scope = self.mock.call_args.args[0]
        self.assertEqual(scope['headers'], [(b'x-session-id', session), (b'cookie', b'user_pref=dark_mode')])
        self.assertEqual(scope['cookies'], {'sessionid': session.decode()})
        self.assertEqual(scope['user'].username, "sudo")
        self.assertEqual(scope['user'].pk, self.sudo.pk)

