
from django.http import JsonResponse

class JsonResponseFailure(JsonResponse):
    def __init__ (self, status: int, err_msg: str):
        super().__init__({ "code": status, "message": err_msg }, status = status)
class Json400(JsonResponseFailure):
    def __init__ (self, err_msg: str):
        super().__init__(400, err_msg)
class Json401(JsonResponseFailure):
    def __init__ (self, err_msg: str):
        super().__init__(401, err_msg)
class Json403(JsonResponseFailure):
    def __init__ (self, err_msg: str):
        super().__init__(403, err_msg)
