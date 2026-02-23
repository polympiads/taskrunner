
from django.test import RequestFactory, TestCase, Client, override_settings
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User
from ccs.auth.middleware import HeaderSessionMiddleware

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
