
import asyncio

from typing import Literal
from django.conf import settings

class SandboxManager:
    __instance : "SandboxManager | Literal[None]" = None
    ids_queue  : asyncio.Queue = None

    def __init__(self):
        if self.ids_queue is None:
            self.ids_queue = asyncio.Queue()

            for idx in range(settings.MAX_NB_SANDBOX):
                self.ids_queue.put_nowait(idx)

    def setup_worker (self, worker_id: int):
        while not self.ids_queue.empty():
            self.ids_queue.get_nowait()
        for idx in range(settings.MAX_NB_SANDBOX):
            self.ids_queue.put_nowait(idx + worker_id * settings.MAX_NB_SANDBOX)

    async def allocate_id (self) -> int:
        return await self.ids_queue.get()
    async def free_id (self, idx: int):
        await self.ids_queue.put(idx)

    @staticmethod
    def instance () -> "SandboxManager":
        return SandboxManager()
    def __new__(cls, *args, **kwargs):
        if cls.__instance is None:
            cls.__instance = super().__new__(cls, *args, **kwargs)
        
        return cls.__instance
