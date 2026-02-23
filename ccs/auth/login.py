
import json
from typing import Dict

from django.contrib.auth import authenticate, login
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from ccs.utils.responses import Json400, Json401

REV_API_LOGIN = "login"

@csrf_exempt
def api_login(request: HttpRequest):
    username = request.GET.get('username', None)
    if username is None:
        return Json400("Missing field 'username'")
    
    password = request.GET.get('password', None)
    if password is None:
        return Json400("Missing field 'password'")

    user = authenticate(username=username, password=password)
    if user:
        login(request, user)
        
        return JsonResponse({ 'session_id' : request.session.session_key })
    return Json401("Invalid credentials")
