
import asyncio
import unittest

from sandbox.manager import SandboxManager, MAX_NB_SANDBOX

class TestSandboxManager (unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        SandboxManager._SandboxManager__instance = None
    def tearDown(self):
        SandboxManager._SandboxManager__instance = None

    async def test_allocate_id (self):
        manager = SandboxManager.instance()

        for idx in range (MAX_NB_SANDBOX):
            self.assertEqual( await manager.allocate_id(), idx )

        with self.assertRaises(asyncio.TimeoutError):
            async with asyncio.timeout(0.1):
                await manager.allocate_id()
    async def test_free_id (self):
        manager = SandboxManager.instance()

        self.assertEqual( await manager.allocate_id(), 0 )

        for idx in range (1, MAX_NB_SANDBOX):
            self.assertEqual( await manager.allocate_id(), idx )

        with self.assertRaises(asyncio.TimeoutError):
            async with asyncio.timeout(0.1):
                await manager.allocate_id()

        await manager.free_id(0)
        self.assertEqual( await manager.allocate_id(), 0 )
        
        with self.assertRaises(asyncio.TimeoutError):
            async with asyncio.timeout(0.1):
                await manager.allocate_id()
    async def test_free_id_during_allocate (self):
        manager = SandboxManager.instance()

        for idx in range (MAX_NB_SANDBOX):
            self.assertEqual( await manager.allocate_id(), idx )
        with self.assertRaises(asyncio.TimeoutError):
            async with asyncio.timeout(0.1):
                await manager.allocate_id()
        
        async def free_back_0 ():
            await asyncio.sleep(0.5)
            await manager.free_id(0)

        async with asyncio.timeout(1):
            _, res = await asyncio.gather( free_back_0(), manager.allocate_id() )
            self.assertEqual(res, 0)
        with self.assertRaises(asyncio.TimeoutError):
            async with asyncio.timeout(0.25):
                _, res = await asyncio.gather( free_back_0(), manager.allocate_id() )
