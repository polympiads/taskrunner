
import unittest

from storecli.base import BaseStorageClient


class TestBaseStorageClient (unittest.IsolatedAsyncioTestCase):
    async def test_all (self):
        with self.assertRaises(NotImplementedError):
            await BaseStorageClient().upload( "/usr/bin/python3", "python3" )
        with self.assertRaises(NotImplementedError):
            await BaseStorageClient().download( "python3" )
        with self.assertRaises(NotImplementedError):
            await BaseStorageClient().delete( "python3" )
        with self.assertRaises(NotImplementedError):
            BaseStorageClient().reserve()
