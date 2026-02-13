
import os
from django.conf import settings
from django.http import HttpRequest, HttpResponseBadRequest, JsonResponse
import uuid6

def chunks_from_location (uuid: uuid6.UUID, sep = os.path.sep) -> str:
    location = str(uuid).replace("-", "")

    return location[:4] + sep + location[4:6] + sep + location
def path_from_location (uuid: uuid6.UUID) -> str:
    result = os.path.join(settings.STORAGE_SERVER_LOCATION, chunks_from_location(uuid))
    os.makedirs( os.path.dirname(result), exist_ok=True )

    return result

def extract_location (request: HttpRequest):
    location = request.GET.get('location')
    if not location:
        return None, HttpResponseBadRequest("missing 'location' from GET parameters")

    try:
        loc_uuid = uuid6.UUID(location)

        if loc_uuid.version != 7:
            return None, HttpResponseBadRequest("location should be valid UUID: Wrong version (should be 7)")
        
        return loc_uuid, None
    except ValueError:
        return None, HttpResponseBadRequest("location should be valid UUID: Wrong format")