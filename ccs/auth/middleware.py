
from channels.auth import AuthMiddleware
from channels.sessions import SessionMiddlewareStack
from django.conf import settings
from django.contrib.sessions.middleware import SessionMiddleware as DjangoSessionMiddleware
from channels.sessions import CookieMiddleware, SessionMiddleware as ChannelsSessionMiddleware

class HeaderSessionMiddleware (DjangoSessionMiddleware):
    def process_request(self, request):
        session_key = request.headers.get('X-Session-ID')

        request.session = self.SessionStore(session_key)

class ChannelsCookieSessionInjectorMiddleware:
    def __init__(self, inner):
        self.inner = inner
    
    async def __call__ (self, scope, receive, send):
        headers = dict(scope.get("headers", []))
        session_id = headers.get(b"x-session-id")

        if "cookies" not in scope:
            scope["cookies"] = {}
        if session_id:
            cookie_name = settings.SESSION_COOKIE_NAME
            scope["cookies"][cookie_name] = session_id.decode()

        return await self.inner(scope, receive, send)

def SessionHeaderAuthenticationStack (inner):
    return CookieMiddleware(
        ChannelsCookieSessionInjectorMiddleware(
            ChannelsSessionMiddleware(
                AuthMiddleware(inner))))
