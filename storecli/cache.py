
from typing import Dict
from storecli.base import BaseStorageClient

class CacheClient(BaseStorageClient):
    _cache: Dict[str, str]
    
    def __init__ (self, client: BaseStorageClient):
        self.client = client
        self._cache = {}
    
    async def download(self, location):
        if location in self._cache:
            return self._cache[location]

        result = self._cache[location] = await self.client.download(location)
        return result
    async def upload(self, file, location):
        return await self.client.upload(file, location)
    async def delete(self, location):
        return await self.client.delete(location)
    def reserve(self):
        return self.client.reserve()
