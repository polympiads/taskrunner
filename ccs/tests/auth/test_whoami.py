
import json

from django.http import JsonResponse
from django.test import RequestFactory, TransactionTestCase, override_settings

from ccs.auth.login import api_login
from ccs.auth.whoami import WhoAmIView

from django.contrib.auth.models import User

class TestWhoAmI (TransactionTestCase):
    def setUp(self):
        self.reqfact = RequestFactory()
        self.view = WhoAmIView.as_view()

        self.user = User.objects.create_user(username = "user", password = "password")
        self.staff = User.objects.create_user(username = "staff", password = "password", is_staff = True)
        self.t23 = User.objects.create_user(username = "t23", password = "password", first_name = "Team 23")
        self.s22 = User.objects.create_user(username = "s22", password = "password", is_staff = True, first_name = "Staff 22")

    def assertContent (self, content, *args, **kwargs):
        response: JsonResponse = self.client.get("/whoami/", *args, **kwargs)

        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, 200)

        raw_bytes = response.content
        self.assertEqual(json.loads(raw_bytes), content)
    def assertContentForUser (self, content, user):
        json_resp = self.client.get("/login/", data = { "username": user, "password": "password" })

        self.assertEqual(json_resp.status_code, 200)

        raw_bytes = json_resp.content
        raw_json  = json.loads(raw_bytes)

        session_id = raw_json['session_id']

        self.assertContent(content, header = { "X-Session-ID": session_id })
    @override_settings(ROOT_URLCONF="ccs.urls")
    def test_logged_out (self):
        self.assertContent({ "is_authenticated": False })
    @override_settings(ROOT_URLCONF="ccs.urls")
    def test_logged_in (self):
        self.assertContentForUser({ "id": str(self.user.pk), "is_authenticated": True, "is_staff": False, "username": "user" }, "user")
    @override_settings(ROOT_URLCONF="ccs.urls")
    def test_staff (self):
        self.assertContentForUser({ "id": str(self.staff.pk), "is_authenticated": True, "is_staff": True, "username": "staff" }, "staff")
    @override_settings(ROOT_URLCONF="ccs.urls")
    def test_first_name (self):
        self.assertContentForUser({ "id": str(self.t23.pk), "is_authenticated": True, "is_staff": False, "username": "t23", "display_name": "Team 23" }, "t23")
    @override_settings(ROOT_URLCONF="ccs.urls")
    def test_first_name_and_staff (self):
        self.assertContentForUser({ "id": str(self.s22.pk), "is_authenticated": True, "is_staff": True, "username": "s22", "display_name": "Staff 22" }, "s22")
