
import unittest
from unittest.mock import AsyncMock, patch

import aiofiles

from storecli.cache import CacheClient
from storecli.error import DownloadError
from storecli.inmemory import InMemoryStorageClient

class TestCacheClient(unittest.IsolatedAsyncioTestCase):
    def setUp (self):
        self.inmemory = InMemoryStorageClient("/tmp")
        self.cache    = CacheClient(self.inmemory)

        self.client = self.cache

    async def test_download_not_exists (self):
        with self.assertRaises(DownloadError):
            await self.client.download( "main.cpp" )
    async def test_download (self):
        self.inmemory.put("main.cpp", b"int main () {}", ".cpp")

        location = await self.client.download( "main.cpp" )
        assert location.startswith("/tmp/")

        sub_location = location[5:]
        assert sub_location.endswith(".cpp")
        assert sub_location.count(".") == 1
        assert sub_location.count("/") == 0

        with patch("storecli.inmemory.InMemoryStorageClient.download", AsyncMock) as mock:
            mock.side_effect = DownloadError
            
            new_location = await self.client.download( "main.cpp" )

            self.assertEqual(location, new_location)
    async def test_upload (self):
        async with aiofiles.open("/tmp/test_main.cpp", "wb") as file:
            await file.write(b"int main () {}")

        await self.client.upload( "/tmp/test_main.cpp", "main.cpp" )
        self.assertEqual( self.inmemory.in_memory, { "main.cpp": (b"int main () {}", ".cpp") } )
    async def test_delete (self):
        self.inmemory.put("main.cpp", b"int main () {}", ".cpp")
        await self.client.delete("main.cpp")
        self.assertEqual(self.inmemory.in_memory, {})
    async def test_reserve (self):
        with patch("storecli.inmemory.uuid") as uuid:
            uuid.uuid4 = lambda : "hi"
            self.assertEqual( await self.client.reserve(), "hi" )
