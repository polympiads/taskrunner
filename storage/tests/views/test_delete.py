
import os
import shutil
import tempfile

from django.test import RequestFactory, TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
import uuid6

from storage.models import StorageEntry
from storage.utils import path_from_location
from storage.views.delete import FileDeleteView
from storage.views.upload import FileUploadView


TEST_DIR = tempfile.mkdtemp()

@override_settings(STORAGE_SERVER_LOCATION=TEST_DIR)
class FileDeleteViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.url = '/delete/'

        self.loc_v7 = str(uuid6.uuid7())
        file_content = b"test code content"
        uploaded_file = SimpleUploadedFile("code.cpp", file_content)
        
        request  = self.factory.post(f"/upload/?location={self.loc_v7}&extension=.cpp", {'file': uploaded_file})
        response = FileUploadView.as_view()(request)

    def tearDown(self):
        shutil.rmtree(TEST_DIR, ignore_errors=True)
        os.mkdir(TEST_DIR)

    def test_delete_works (self):
        request  = self.factory.delete(f"{self.url}?location={self.loc_v7}")
        response = FileDeleteView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(os.path.exists( path_from_location(self.loc_v7) ))
        self.assertEqual(0, StorageEntry.objects.count())
    def test_download_location_does_not_exist (self):
        request  = self.factory.delete(f"{self.url}?location={uuid6.uuid7()}")
        response = FileDeleteView.as_view()(request)

        self.assertEqual(response.status_code, 400)
        self.assertTrue (os.path.exists( path_from_location(self.loc_v7) ))
        self.assertEqual(1, StorageEntry.objects.count())
    def test_download_invalid_location (self):
        request  = self.factory.delete(f"{self.url}?location=not-uuid7")
        response = FileDeleteView.as_view()(request)

        self.assertEqual(response.status_code, 400)
        self.assertTrue (os.path.exists( path_from_location(self.loc_v7) ))
        self.assertEqual(1, StorageEntry.objects.count())
