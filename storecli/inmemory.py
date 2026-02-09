
import os
import uuid

from typing import Dict, Tuple

import aiofiles

from storecli.base import BaseStorageClient
from storecli.error import DownloadError

class InMemoryStorageClient (BaseStorageClient):
    in_memory: Dict[str, Tuple[bytes, str]] # content and extension

    def __init__(self, download_dir: str):
        super().__init__()

        self.download_dir = download_dir
        self.in_memory = {}

        os.makedirs(download_dir, exist_ok=True)

    async def download(self, location):
        _content = self.in_memory.get(location, None)
        if _content is None:
            raise DownloadError(f"Could not find object at location {location}")

        content, extension = _content
        # This is a test implementation so we don't care about collisions
        #   for the true downloader, we need to check that it doesn't exist yet.
        file = os.path.join( self.download_dir, str( uuid.uuid4() ) + extension )

        async with aiofiles.open(file, "wb") as fw:
            await fw.write(content)
        
        return file
    async def upload(self, file, location):
        file_base, file_ext = os.path.splitext(os.path.basename(file))
        
        async with aiofiles.open(file, "rb") as fr:
            self.in_memory[location] = (
                await fr.read(),
                file_ext
            )
    async def delete(self, location):
        del self.in_memory[location]

    def put (self, location: str, content: bytes, extension: str):
        self.in_memory[location] = (content, extension)
