
from django.contrib.sessions.middleware import SessionMiddleware

class HeaderSessionMiddleware (SessionMiddleware):
    def process_request(self, request):
        session_key = request.headers.get('X-Session-ID')

        request.session = self.SessionStore(session_key)
