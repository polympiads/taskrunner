
"""
Storage Base Client
"""
class BaseStorageClient:
    async def download (self, location: str) -> "str":
        raise NotImplementedError()
    async def upload (self, file: str, location: str):
        raise NotImplementedError()
    async def delete (self, location: str):
        raise NotImplementedError()
    async def reserve (self) -> str:
        raise NotImplementedError()
