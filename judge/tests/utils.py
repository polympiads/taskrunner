
import asyncio
import os
import unittest

from django.conf import settings
from sandbox.manager import SandboxManager

def can_test_judge ():
    if "TEST_JUDGE" in os.environ.keys():
        return True
    return False

def skip_lang_tests ():
    return unittest.skipUnless(can_test_judge, reason = "Can only test languages in judge")

async def inspect_queue(q: asyncio.Queue):
    items = []
    while not q.empty():
        items.append(q.get_nowait())
    
    for item in items:
        await q.put(item)
        
    return items
async def assert_all_sandbox_freed ():
    manager = SandboxManager.instance()
    assert set(await inspect_queue(manager.ids_queue)) == set(range(settings.MAX_NB_SANDBOX))
