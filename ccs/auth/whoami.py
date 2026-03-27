
from typing import NotRequired, TypedDict

from django.http import HttpRequest, JsonResponse
from django.views import View


REV_WHO_AM_I = "whoami"

class WhoAmIJSON (TypedDict):
    """
    Id of the user
      Is present if and only if is authenticated
    """
    id: str
    """
    Username of the user
      Is present if and only if is authenticated
    """
    username : NotRequired[str]

    """
    The display name of the user
      If is absent, you should default to using the username
    """
    display_name : NotRequired[str]

    """
    Represents if the user is staff
      Is present if and only if is authenticated
    """
    is_staff : NotRequired[bool]

    """
    Represents if the user is authenticated
    """
    is_authenticated : bool

class WhoAmIView(View):
    def get (self, request: HttpRequest):
        json: WhoAmIJSON = {
            "is_authenticated": request.user.is_authenticated
        }

        if request.user.is_authenticated:
            if request.user.first_name != "":
                json["display_name"] = request.user.first_name
            
            json["is_staff"] = request.user.is_staff
            json["username"] = request.user.username
            json["id"] = str(request.user.pk)

        return JsonResponse( json, status = 200 )
