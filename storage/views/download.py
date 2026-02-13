
from django.http  import FileResponse, HttpRequest, HttpResponseBadRequest, JsonResponse
from django.views import View
import uuid6

from storage.models import StorageEntry
from storage.utils import extract_location, path_from_location

class FileDownloadView (View):
    def get (self, request: HttpRequest):
        location, location_response = extract_location(request)
        if location_response is not None:
            return location_response

        entries = StorageEntry.objects.filter(id = location)
        if len(entries) != 1:
            return HttpResponseBadRequest("invalid location")

        file_path = path_from_location( location )
        
        response = FileResponse(open(file_path, 'rb'), as_attachment=True)
        response.headers['X-Extension'] = entries[0].extension

        return response
