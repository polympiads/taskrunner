
from django.http  import HttpRequest, HttpResponse, HttpResponseBadRequest, JsonResponse
from django.views import View
import uuid6

from storage.models import StorageEntry
from storage.utils import extract_location, path_from_location

class FileUploadView (View):
    def post (self, request: HttpRequest):
        location, location_response = extract_location(request)
        if location_response is not None:
            return location_response
        
        extension : str = request.GET.get('extension')
        if not extension:
            return HttpResponseBadRequest("missing 'extension' from GET parameters")

        uploaded_file = request.FILES.get('file')
        if not uploaded_file:
            return HttpResponseBadRequest("could not find uploaded file")

        file_path = path_from_location( location )
        
        StorageEntry.objects.create(id = location, extension = extension)

        with open(file_path, "wb") as file:
            for chunk in uploaded_file.chunks():
                file.write(chunk)

        return HttpResponse("ok")
