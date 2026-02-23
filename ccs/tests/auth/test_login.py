
import json
from django.test import TestCase

from django.contrib.auth.models import User
from django.test import Client, override_settings
from django.contrib.sessions.models import Session

class TestLogin (TestCase):
    def setUp(self):
        self.user = User.objects.create_user("user", password = "password")
        self.sudo = User.objects.create_superuser("sudo", password = "password")
        self.cli = Client()
    
    def assertRequestFails (self, input, output, status = 400):
        response = self.cli.get("/login/", data=input)
        self.assertEqual(response.json(), {"code": status, "message": output})

    @override_settings(ROOT_URLCONF="ccs.urls")
    def test_login_fails (self):
        self.assertRequestFails({}, "Missing field 'username'")
        self.assertRequestFails({ "username": "user" }, "Missing field 'password'")
        self.assertRequestFails({ "username": "user", "password": "invalid" }, "Invalid credentials", status = 401)

    @override_settings(ROOT_URLCONF="ccs.urls")
    def test_login_works (self):
        response = self.cli.get("/login/", data = { "username": "user", "password": "password" })
        content = response.json()
        session_id = content['session_id']
        session = Session.objects.get(session_key=session_id)
        session_data = session.get_decoded()
        self.assertEqual(session_data.get('_auth_user_id'), str(self.user.pk))

        # Reset client since cookies block the client from logging in.
        self.cli = Client()
        response = self.cli.get("/login/", data = { "username": "sudo", "password": "password" })
        content = response.json()
        session_id = content['session_id']
        session = Session.objects.get(session_key=session_id)
        session_data = session.get_decoded()
        self.assertEqual(session_data.get('_auth_user_id'), str(self.sudo.pk))
