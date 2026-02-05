
import asyncio

from typing import Literal
from config import MAX_NB_SANDBOX

class SandboxManager:
    __instance : "SandboxManager | Literal[None]" = None
    ids_queue  : asyncio.Queue

    def __init__(self):
        self.ids_queue = asyncio.Queue()

        for idx in range(MAX_NB_SANDBOX):
            self.ids_queue.put_nowait(idx)

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
