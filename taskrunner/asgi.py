"""
ASGI config for taskrunner project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os

from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware

from channels.auth import AuthMiddleware
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.sessions import CookieMiddleware, SessionMiddleware

from django.core.asgi import get_asgi_application
from django.urls import re_path

from ccs.auth.middleware import SessionHeaderAuthenticationStack
from ccs.views.eventfeed import EventFeedConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'taskrunner.settings')

stream_pipeline = SessionHeaderAuthenticationStack(
    URLRouter([
        re_path(r"^", EventFeedConsumer.as_asgi())
    ])
)

application = OpenTelemetryMiddleware(ProtocolTypeRouter(
    {
        "http": URLRouter([
            re_path(r"^contests/(?P<id>\d+)/eventfeed/", stream_pipeline),
            re_path(r"^", get_asgi_application())
        ])
    }
))
