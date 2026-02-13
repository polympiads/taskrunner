
import os
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.views import View

from storage.models import StorageEntry
from storage.utils import extract_location, path_from_location

class FileDeleteView (View):
    def delete (self, request: HttpRequest):
        location, location_response = extract_location(request)
        if location_response is not None:
            return location_response

        num_entries, _ = StorageEntry.objects.filter(id = location) \
            .delete()
        
        if num_entries == 0:
            return HttpResponseBadRequest("such location does not exist")

        file_path = path_from_location( location )
        os.remove(file_path)
        
        return HttpResponse("ok, deleted")
