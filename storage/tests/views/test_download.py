
import os
import shutil
import tempfile

from django.test import RequestFactory, TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
import uuid6

from storage.views.download import FileDownloadView
from storage.views.upload import FileUploadView


TEST_DIR = tempfile.mkdtemp()

@override_settings(STORAGE_SERVER_LOCATION=TEST_DIR)
class FileDownloadViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.url = '/download/'

        self.loc_v7 = str(uuid6.uuid7())
        file_content = b"test code content"
        uploaded_file = SimpleUploadedFile("code.cpp", file_content)
        
        request  = self.factory.post(f"/upload/?location={self.loc_v7}&extension=.cpp", {'file': uploaded_file})
        response = FileUploadView.as_view()(request)

    def tearDown(self):
        shutil.rmtree(TEST_DIR, ignore_errors=True)
        os.mkdir(TEST_DIR)

    def test_download_works (self):
        request  = self.factory.get(f"{self.url}?location={self.loc_v7}")
        response = FileDownloadView.as_view()(request)

        file_content = b"".join(response.streaming_content)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(file_content, b"test code content")
        self.assertEqual(response.headers['X-Extension'], ".cpp")
    def test_download_location_does_not_exist (self):
        request  = self.factory.get(f"{self.url}?location={uuid6.uuid7()}")
        response = FileDownloadView.as_view()(request)

        self.assertEqual(response.status_code, 400)
    def test_download_invalid_location (self):
        request  = self.factory.get(f"{self.url}?location=not-uuid7")
        response = FileDownloadView.as_view()(request)

        self.assertEqual(response.status_code, 400)
