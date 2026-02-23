
import json

from django.test import Client, TestCase, override_settings
from django.contrib.auth.models import User

from ccs.models.contest import Contest

class TestCreateContestView (TestCase):
    def setUp(self):
        self.user = User.objects.create_user("user", password = "password")
        self.sudo = User.objects.create_superuser("sudo", password = "password")

        self.new_settings = override_settings(
            ROOT_URLCONF="ccs.urls",            
            MIDDLEWARE = [
                'django.middleware.security.SecurityMiddleware',
                'ccs.auth.middleware.HeaderSessionMiddleware',
                'django.middleware.common.CommonMiddleware',
                'django.middleware.csrf.CsrfViewMiddleware',
                'django.contrib.auth.middleware.AuthenticationMiddleware',
                'django.contrib.messages.middleware.MessageMiddleware',
                'django.middleware.clickjacking.XFrameOptionsMiddleware',
            ]
        )
        self.new_settings.__enter__()

        self.session_user = Client().get("/login/", { "username": "user", "password": "password" }).json()['session_id']
        self.session_sudo = Client().get("/login/", { "username": "sudo", "password": "password" }).json()['session_id']
    def tearDown(self):
        self.new_settings.__exit__(None, None, None)

    def assertWorks (self, session_key, content):
        response = Client().post(
            "/contests/",
            data = json.dumps(content) if content is not None else "",
            content_type = "application/json",
            headers = { "X-Session-ID": session_key })
        self.assertEqual(response.status_code, 200)
        return response.json()
    def assertFailure (self, session_key, content, message, status = 400):
        response = Client().post(
            "/contests/",
            data = json.dumps(content) if content is not None else "",
            content_type = "application/json",
            headers = { "X-Session-ID": session_key })
        self.assertEqual(response.json()['code'], status)
        self.assertEqual(response.json()['message'], message)

    def test_create_failure (self):
        self.assertFailure(self.session_user, None, "Missing permissions", 403)
        self.assertFailure(self.session_sudo, None, "Malformed JSON body")
        self.assertFailure(self.session_sudo, [], "Malformed JSON body")
        self.assertFailure(self.session_sudo, {}, "Field 'name' shouldn't be empty.")
        self.assertFailure(self.session_sudo, { "name": [] }, "Field 'name' should be a string.")
        self.assertFailure(self.session_sudo, { "name": "hc2" * 64 }, "Field 'name' shouldn't have length bigger than 64")
        self.assertFailure(self.session_sudo, { "name": "hc2" }, "Field 'duration' should exist")
        self.assertFailure(self.session_sudo, { "name": "hc2", "duration": [] }, "Field 'duration' should be a string")
        self.assertFailure(self.session_sudo, { "name": "hc2", "duration": "fjieoj" }, "Field 'duration': Invalid relative time format: fjieoj")
        self.assertFailure(self.session_sudo, { "name": "hc2", "duration": "5:00:00" }, "Field 'penalty_time' should exist")
        self.assertFailure(self.session_sudo, { "name": "hc2", "duration": "5:00:00", "penalty_time": [] }, "Field 'penalty_time' should be a string")
        self.assertFailure(self.session_sudo, { "name": "hc2", "duration": "5:00:00", "penalty_time": "fjieoj" }, "Field 'penalty_time': Invalid relative time format: fjieoj")
        self.assertFailure(self.session_sudo, { "name": "hc2", "duration": "5:00:00", "penalty_time": "0:20:00" }, "Field 'visibility' should exist")
        self.assertFailure(self.session_sudo, { "name": "hc2", "duration": "5:00:00", "penalty_time": "0:20:00", "visibility": "..." }, "Field 'visibility' should be either \"public\" or \"private\"")
        self.assertFailure(self.session_sudo, { "name": "hc2", "duration": "5:00:00", "penalty_time": "0:20:00", "visibility": "public" }, "There should be exactly one of the 'start_time' and 'countdown_pause_time' fields.")
    def test_simple_create (self):
        result = self.assertWorks(self.session_sudo, { "name": "hc2", "duration": "5:00:00", "penalty_time": "0:20:00", "visibility": "public", "start_time": "2026-02-23T09:52:47.187Z" })
        self.assertEqual(result, {
            "duration": "5:00:00.000",
            "id": str(Contest.objects.all()[0].pk),
            "formal_name": "hc2",
            "name": "hc2",
            "penalty_time": "0:20:00.000",
            "scoreboard_freeze_duration": "0:00:00.000",
            "scoreboard_type": "pass-fail",
            "start_time": "2026-02-23T09:52:47.187Z"
        })
    def test_advanced_create (self):
        result = self.assertWorks(self.session_sudo, {
            "name": "hc2-2026",
            "formal_name": "Helvetic Coding Contest 2026",
            "duration": "4:30:00",
            "scoreboard_freeze_duration": "1:00:00",
            "scoreboard_thaw_time": "2026-02-24T09:52:47.187Z",
            "penalty_time": "0:20:00",
            "visibility": "private",
            "start_time": "2026-02-23T09:52:47.187Z"
        })
        self.assertEqual(result, {
            "id": str(Contest.objects.all()[0].pk),
            "name": "hc2-2026",
            "formal_name": "Helvetic Coding Contest 2026",
            "duration": "4:30:00.000",
            "scoreboard_freeze_duration": "1:00:00.000",
            "scoreboard_thaw_time": "2026-02-24T09:52:47.187Z",
            "scoreboard_type": "pass-fail",
            "penalty_time": "0:20:00.000",
            "start_time": "2026-02-23T09:52:47.187Z"
        })
        

class TestContestView (TestCase):
    def setUp(self):
        self.user = User.objects.create_user("user", password = "password")
        self.sudo = User.objects.create_superuser("sudo", password = "password")

        self.new_settings = override_settings(
            ROOT_URLCONF="ccs.urls",            
            MIDDLEWARE = [
                'django.middleware.security.SecurityMiddleware',
                'ccs.auth.middleware.HeaderSessionMiddleware',
                'django.middleware.common.CommonMiddleware',
                'django.middleware.csrf.CsrfViewMiddleware',
                'django.contrib.auth.middleware.AuthenticationMiddleware',
                'django.contrib.messages.middleware.MessageMiddleware',
                'django.middleware.clickjacking.XFrameOptionsMiddleware',
            ]
        )
        self.new_settings.__enter__()

        self.session_user = Client().get("/login/", { "username": "user", "password": "password" }).json()['session_id']
        self.session_sudo = Client().get("/login/", { "username": "sudo", "password": "password" }).json()['session_id']
    def tearDown(self):
        self.new_settings.__exit__(None, None, None)

    def assertWorks (self, session_key, content):
        response = Client().post(
            "/contests/",
            data = json.dumps(content) if content is not None else "",
            content_type = "application/json",
            headers = { "X-Session-ID": session_key })
        self.assertEqual(response.status_code, 200)
        return response.json()
    def test_view_as_user (self):
        result1 = self.assertWorks(self.session_sudo, { "name": "hc2-2025", "duration": "5:00:00", "penalty_time": "0:20:00", "visibility": "public", "start_time": "2025-02-23T09:52:47.187Z" })
        result2 = self.assertWorks(self.session_sudo, { "name": "hc2-2026", "duration": "5:00:00", "penalty_time": "0:20:00", "visibility": "private", "start_time": "2026-02-23T09:52:47.187Z" })
        
        result = Client().get("/contests/", headers = { "X-Session-ID": self.session_user })
        self.assertEqual(result.json(), [ result1 ])
    def test_view_as_sudo (self):
        result1 = self.assertWorks(self.session_sudo, { "name": "hc2-2025", "duration": "5:00:00", "penalty_time": "0:20:00", "visibility": "public", "start_time": "2025-02-23T09:52:47.187Z" })
        result2 = self.assertWorks(self.session_sudo, { "name": "hc2-2026", "duration": "5:00:00", "penalty_time": "0:20:00", "visibility": "private", "start_time": "2026-02-23T09:52:47.187Z" })
        
        result = Client().get("/contests/", headers = { "X-Session-ID": self.session_sudo })
        self.assertEqual(result.json(), [ result1, result2 ])
