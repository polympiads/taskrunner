import io
import json
import os
import shutil
import tempfile
import uuid
from django.http import JsonResponse
import uuid6
from django.test import TestCase, override_settings, RequestFactory
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from storage.models import StorageEntry
from storage.views import FileUploadView

# Create a temporary directory for test file storage
TEST_DIR = tempfile.mkdtemp()

@override_settings(STORAGE_SERVER_LOCATION=TEST_DIR)
class FileUploadViewTest(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.url = '/upload/'

    def tearDown(self):
        shutil.rmtree(TEST_DIR, ignore_errors=True)
        os.mkdir(TEST_DIR)

    def test_upload_success(self):
        loc_v7 = str(uuid6.uuid7())
        file_content = b"test code content"
        uploaded_file = SimpleUploadedFile("code.cpp", file_content)
        
        request = self.factory.post(f"{self.url}?location={loc_v7}&extension=.cpp", {'file': uploaded_file})
        
        response = FileUploadView.as_view()(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'ok')

        assert len(os.listdir(TEST_DIR)) == 1
        assert len(os.listdir(TEST_DIR + f"/{loc_v7[0:4]}")) == 1
        assert len(os.listdir(TEST_DIR + f"/{loc_v7[0:4]}/{loc_v7[4:6]}")) == 1
        with open(TEST_DIR + f"/{loc_v7[0:4]}/{loc_v7[4:6]}/{loc_v7}", "r") as file:
            assert file.read() == "test code content"
        assert StorageEntry.objects.all().count() == 1
        entry = StorageEntry.objects.all()[0]
        self.assertEqual(str(entry.id), str(loc_v7))
        self.assertEqual(str(entry.extension), ".cpp")

    def test_missing_location(self):
        request = self.factory.post(f"{self.url}?extension=cpp")
        response = FileUploadView.as_view()(request)
        
        self.assertEqual(response.status_code, 400)
        assert len(os.listdir(TEST_DIR)) == 0
        assert StorageEntry.objects.all().count() == 0
    def test_missing_extension(self):
        loc_v7 = str(uuid6.uuid7())
        request = self.factory.post(f"{self.url}?location={loc_v7}")
        response = FileUploadView.as_view()(request)
        
        self.assertEqual(response.status_code, 400)
        assert len(os.listdir(TEST_DIR)) == 0
        assert StorageEntry.objects.all().count() == 0
        
    def test_invalid_uuid_format(self):
        request = self.factory.post(f"{self.url}?location=not-a-uuid&extension=cpp")
        response = FileUploadView.as_view()(request)
        
        self.assertEqual(response.status_code, 400)
        assert len(os.listdir(TEST_DIR)) == 0
        assert StorageEntry.objects.all().count() == 0

    def test_wrong_uuid_version(self):
        loc_v4 = str(uuid.uuid4())
        request = self.factory.post(f"{self.url}?location={loc_v4}&extension=cpp")
        response = FileUploadView.as_view()(request)
        
        self.assertEqual(response.status_code, 400)
        assert len(os.listdir(TEST_DIR)) == 0
        assert StorageEntry.objects.all().count() == 0

    def test_missing_file(self):
        loc_v7 = str(uuid6.uuid7())
        request = self.factory.post(f"{self.url}?location={loc_v7}&extension=cpp")
        response = FileUploadView.as_view()(request)
        
        self.assertEqual(response.status_code, 400)
        assert len(os.listdir(TEST_DIR)) == 0
        assert StorageEntry.objects.all().count() == 0
