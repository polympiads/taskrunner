
import os
import requests
import uuid6

from storage.utils import path_from_location
from storecli.base import BaseStorageClient
from asgiref.sync import sync_to_async

from storecli.error import DownloadError
from storecli.telemetry import start_as_current_span

class NetworkClient (BaseStorageClient):
    class InternalError (RuntimeError): pass

    def __init__ (self, prefix: str, storage_path: str, chunk_size: int = 8192):
        if prefix.endswith("/"):
            prefix = prefix[:-1]
        
        self.prefix = prefix
        self.storage_path = storage_path
        os.makedirs(storage_path, exist_ok=True)
        self.chunk_size = chunk_size

    def url (self, part: str):
        return self.prefix + part

    @start_as_current_span("Network.upload")
    def sync_upload(self, file, location):
        with open(file, "rb") as file_reader:
            files = {
                "file": (os.path.basename(file), file_reader, "application/octet-stream")
            }
            params = { "location": location, "extension": os.path.splitext(file)[1] }

            response = requests.post(
                self.url("/upload/"), files = files, params = params)
            
            if response.status_code != 200:
                raise NetworkClient.InternalError(response.text)
    @start_as_current_span("Network.download")
    def sync_download(self, location):
        with requests.get(
                self.url( "/download/" ),
                params = { "location" : location },
                stream = True
            ) as response:
            if response.status_code != 200:
                raise DownloadError(response.text)
            
            extension = response.headers.get('X-Extension')
            if extension is None:
                raise DownloadError("missing extension header")
            
            # The post path allows to avoid a download overriding a file from
            # another worker process when they are running at the same time
            post_path = "-" + str(uuid6.uuid7())
            file_path = path_from_location(location, self.storage_path) + post_path + extension
            os.makedirs( os.path.dirname(file_path), exist_ok=True )

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=self.chunk_size):
                    f.write(chunk)

            return file_path
    @start_as_current_span("Network.delete")
    def sync_delete(self, location):
        response = requests.delete(
            self.url( "/delete/" ),
            params = { "location": location }
        )

        if response.status_code != 200:
            raise NetworkClient.InternalError(response.text)

    async def upload(self, file, location):
        return await sync_to_async(NetworkClient.sync_upload)(self, file, location)
    async def download(self, location):
        return await sync_to_async(NetworkClient.sync_download)(self, location)
    async def delete(self, location):
        return await sync_to_async(NetworkClient.sync_delete)(self, location)

    def reserve(self):
        return str(uuid6.uuid7())
