
import os
from unittest.mock import AsyncMock, MagicMock, patch
import uuid6
import asyncio

from django.test import LiveServerTestCase, override_settings

from storage.models import StorageEntry
from storage.utils import path_from_location
from storecli.error import DownloadError
from storecli.network import NetworkClient

@override_settings(ROOT_URLCONF='storage.urls')
class TestNetworkClient(LiveServerTestCase):
    urls = 'storage.urls'

    def setUp(self):
        self.net_client = NetworkClient( self.live_server_url, "/app/network_storage" )
    
    def test_prefix (self):
        net_client1 = NetworkClient( self.live_server_url, "/app/network_storage" )
        net_client2 = NetworkClient( self.live_server_url + "/", "/app/network_storage" )

        self.assertEqual(net_client1.prefix, net_client2.prefix)
        self.assertEqual(net_client1.prefix, self.live_server_url)

    def test_download_not_exists (self):
        with self.assertRaises(DownloadError):
            asyncio.run( self.net_client.download(
                str(uuid6.uuid7()) ) )
    def test_upload (self):
        self.uuid = str(uuid6.uuid7())

        asyncio.run( self.net_client.upload(__file__, self.uuid) )
        entries = list(StorageEntry.objects.all())
        self.assertEqual(1, len(entries))
        entry = entries[0]
        self.assertEqual(entry.extension, ".py")
        self.assertEqual(str(entry.id), self.uuid)
        self.assertTrue (os.path.exists(path_from_location(self.uuid)))

        with open(__file__, "rb") as file:
            text_expects = file.read()
        with open(path_from_location(self.uuid), "rb") as file:
            text_found = file.read()
        self.assertEqual(text_expects, text_found)
    def test_upload_and_download (self):
        self.uuid = "01234567-89ab-7cde-a012-3456789abcde"

        asyncio.run( self.net_client.upload(__file__, self.uuid) )
        custom_path = asyncio.run( self.net_client.download(self.uuid) )
        self.assertEqual( custom_path, f"/app/network_storage/0123/45/{self.uuid}.py" )
        with open(__file__, "rb") as file:
            text_expects = file.read()
        with open(custom_path, "rb") as file:
            text_found = file.read()
        self.assertEqual(text_expects, text_found)
    def test_delete_not_exists (self):
        self.uuid = str(uuid6.uuid7())

        with self.assertRaises(NetworkClient.InternalError):
            asyncio.run( self.net_client.delete(self.uuid) )
    def test_delete (self):
        self.uuid = str(uuid6.uuid7())

        asyncio.run( self.net_client.upload(__file__, self.uuid) )
        asyncio.run( self.net_client.delete(self.uuid) )
        entries = list(StorageEntry.objects.all())
        self.assertEqual(0, len(entries))
        self.assertFalse(os.path.exists(path_from_location(self.uuid)))

    def test_download_header_missing (self):
        self.uuid = str(uuid6.uuid7())

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {}

        mock_response.__enter__.return_value = mock_response
        
        with patch('requests.get', return_value=mock_response) as mock_get:
            with self.assertRaisesRegex(DownloadError, "missing extension header"):
                asyncio.run( self.net_client.download(self.uuid) )
    def test_upload_fails (self):
        self.uuid = str(uuid6.uuid7())

        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "error"

        with patch('requests.post', return_value=mock_response) as mock_get:
            with self.assertRaisesRegex(NetworkClient.InternalError, "error"):
                asyncio.run( self.net_client.upload(__file__, self.uuid) )

    def test_reserve (self):
        with patch("uuid6.uuid7") as uuid7:
            uuid7.return_value = "hi"

            self.assertEqual(
                self.net_client.reserve(), "hi" )
