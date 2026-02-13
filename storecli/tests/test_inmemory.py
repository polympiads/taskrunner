
import unittest
from unittest.mock import patch

import aiofiles

from storecli.error import DownloadError
from storecli.inmemory import InMemoryStorageClient

class TestInMemoryStorageClient(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.client = InMemoryStorageClient( "/tmp" )
    
    async def test_download_not_exists (self):
        with self.assertRaises(DownloadError):
            await self.client.download( "main.cpp" )
    async def test_download (self):
        self.client.put("main.cpp", b"int main () {}", ".cpp")

        location = await self.client.download( "main.cpp" )
        assert location.startswith("/tmp/")

        location = location[5:]
        assert location.endswith(".cpp")
        assert location.count(".") == 1
        assert location.count("/") == 0
    async def test_upload (self):
        async with aiofiles.open("/tmp/test_main.cpp", "wb") as file:
            await file.write(b"int main () {}")

        await self.client.upload( "/tmp/test_main.cpp", "main.cpp" )
        self.assertEqual( self.client.in_memory, { "main.cpp": (b"int main () {}", ".cpp") } )
    async def test_delete (self):
        self.client.put("main.cpp", b"int main () {}", ".cpp")
        await self.client.delete("main.cpp")
        self.assertEqual(self.client.in_memory, {})
    async def test_reserve (self):
        with patch("storecli.inmemory.uuid") as uuid:
            uuid.uuid4 = lambda : "hi"
            self.assertEqual( await self.client.reserve(), "hi" )
