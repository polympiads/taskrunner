

import asyncio
from datetime import timedelta
import json
import httpx
import threading
from unittest.mock import AsyncMock, patch

from channels.layers import InMemoryChannelLayer, get_channel_layer
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.testing import ChannelsLiveServerTestCase
from django.test import AsyncClient, Client, TransactionTestCase, override_settings
from django.urls import re_path
import requests

from ccs.auth.middleware import SessionHeaderAuthenticationStack
from ccs.models.contest import Contest
from ccs.models.eventfeed import EventFeed
from ccs.models.managers.eventfeed import EventFeedManager, EventFeedKind
from ccs.models.visible import Visibility
from ccs.views.eventfeed import EventFeedConsumer
from django.contrib.auth.models import AnonymousUser, User

def override_layer (**kwargs):
    return override_settings(CHANNEL_LAYERS = { "default": { "BACKEND": "channels.layers.InMemoryChannelLayer" } }, **kwargs)

class FakeEventFeedConsumer(EventFeedConsumer):
    def __init__(self, channel_layer, user, contestid, since = None, sleep_headers: float = 0):
        self.channel_layer = channel_layer
        self.scope = {
            "type": "http",
            "user": user,
            "url_route": { "kwargs": {'id': str(contestid) } },
            "query_string": b"" if since is None else f"since_token={since}".encode() }
        self.base_send = AsyncMock()
        self._bodies: list[bytes] = []
        self.sleep_headers = sleep_headers

    async def send_headers(self, *, status, headers):
        self._status = status
        self._headers = headers

        await asyncio.sleep(self.sleep_headers)

    async def send_body(self, body, *, more_body=False):
        self._bodies.append(body)

class TestEventFeedConsumerExistence (TransactionTestCase):
    def setUp(self):
        self.publicContest = Contest.objects.create(
            name         = "pubct",
            duration     = timedelta(hours=5),
            penalty_time = timedelta(minutes = 20),
            visibility   = Visibility.PUBLIC
        )
        self.privateContest = Contest.objects.create(
            name         = "prict",
            duration     = timedelta(hours=5),
            penalty_time = timedelta(minutes = 20),
            visibility   = Visibility.PRIVATE
        )

        self.user = User.objects.create_user(username = "user", password = "pass")
        self.sudo = User.objects.create_superuser(username = "sudo", password = "pass")
    def verify_consumer (self, content, status = 200):
        _body = b"".join(self.consumer._bodies)
        _json = json.loads(_body)

        self.assertEqual(_json, content)
        self.assertEqual(self.consumer._status, status)
    
    def test_contest_doesnotexist (self):
        for user in [ AnonymousUser(), self.user, self.sudo ]:
            self.consumer = FakeEventFeedConsumer(
                InMemoryChannelLayer(),
                user,
                -1
            )

            asyncio.run( asyncio.wait_for( self.consumer.handle(b""), timeout = 0.25 ) )
            self.verify_consumer({ "code": 404, "message": "Contest does not exist." }, status = 404)
    def test_contest_exists (self):
        for user in [ AnonymousUser(), self.user, self.sudo ]:
            self.consumer = FakeEventFeedConsumer(
                InMemoryChannelLayer(),
                user,
                self.publicContest.pk
            )

            with self.assertRaises(asyncio.TimeoutError):
                asyncio.run( asyncio.wait_for( self.consumer.handle(b""), timeout = 0.25 ) )
    def test_contest_exists_invisible (self):
        for user in [AnonymousUser(), self.user]:
            self.consumer = FakeEventFeedConsumer(
                InMemoryChannelLayer(),
                user,
                self.privateContest.pk
            )
            
            asyncio.run( asyncio.wait_for( self.consumer.handle(b""), timeout = 0.25 ) )
            self.verify_consumer({ "code": 404, "message": "Contest does not exist." }, status = 404)
    def test_contest_exists_private_but_visible (self):
        for user in [self.sudo]:
            self.consumer = FakeEventFeedConsumer(
                InMemoryChannelLayer(),
                user,
                self.privateContest.pk
            )
            
            with self.assertRaises(asyncio.TimeoutError):
                asyncio.run( asyncio.wait_for( self.consumer.handle(b""), timeout = 0.25 ) )

class TestEventFeedConsumerContent (TransactionTestCase):
    def setUp(self):
        self.contest = Contest.objects.create(
            name         = "pubct",
            duration     = timedelta(hours=5),
            penalty_time = timedelta(minutes = 20),
            visibility   = Visibility.PUBLIC
        )

        self.user = User.objects.create_user(username = "user", password = "pass")
        self.sudo = User.objects.create_superuser(username = "sudo", password = "pass")

        # Clear the event feeds that had been created
        EventFeed.objects.all().delete()

    def createObjects (self):
        self.payloads = {}
    
        for viskind, visname in [(Visibility.PUBLIC, "public"), (Visibility.PRIVATE, "private")]:
            for username, user in [("null", None), ("user", self.user), ("sudo", self.sudo)]:
                eventfeed = EventFeed.objects.create(
                    contest = self.contest,
                    owner   = user,

                    visibility  = viskind,
                    raw_payload = json.dumps({ "content": f"{visname}+{username}" })
                )

                self.payloads[f"{visname}+{username}"] = (
                    eventfeed,
                    eventfeed.full_payload
                )

    def verify_consumer (self, *content, status = 200):
        _body = b"".join(self.consumer._bodies)
        _targ = b"".join( list(map(lambda cnt: cnt[1], content)) )

        self.assertEqual(_body.decode(), _targ.decode())
        self.assertEqual(self.consumer._status, status)
    def test_sudo_read_pre (self):
        self.consumer = FakeEventFeedConsumer(
            InMemoryChannelLayer(),
            self.sudo,
            self.contest.pk
        )

        self.createObjects()
        with self.assertRaises(asyncio.TimeoutError):
            asyncio.run( asyncio.wait_for( self.consumer.handle(b""), timeout = 0.25 ) )
        self.verify_consumer(
            self.payloads["public+null"],
            self.payloads["public+user"],
            self.payloads["public+sudo"],
            self.payloads["private+null"],
            self.payloads["private+user"],
            self.payloads["private+sudo"], status = 200)

    def test_user_read_pre (self):
        self.consumer = FakeEventFeedConsumer(
            InMemoryChannelLayer(),
            self.user,
            self.contest.pk
        )

        self.createObjects()
        with self.assertRaises(asyncio.TimeoutError):
            asyncio.run( asyncio.wait_for( self.consumer.handle(b""), timeout = 0.25 ) )
        self.verify_consumer(
            self.payloads["public+null"],
            self.payloads["public+user"],
            self.payloads["public+sudo"],
            self.payloads["private+user"], status = 200)
    def test_anonymous_read_pre (self):
        self.consumer = FakeEventFeedConsumer(
            InMemoryChannelLayer(),
            AnonymousUser(),
            self.contest.pk
        )

        self.createObjects()
        with self.assertRaises(asyncio.TimeoutError):
            asyncio.run( asyncio.wait_for( self.consumer.handle(b""), timeout = 0.25 ) )
        self.verify_consumer(
            self.payloads["public+null"],
            self.payloads["public+user"],
            self.payloads["public+sudo"], status = 200)

    async def createObjectsAsync (self, timeBefore: float = 0.25):
        await asyncio.sleep(timeBefore)
        self.apayloads = {}

        idx = 0
    
        for viskind, visname in [(Visibility.PUBLIC, "public"), (Visibility.PRIVATE, "private")]:
            for username, user in [("null", None), ("user", self.user), ("sudo", self.sudo)]:
                idx += 1
                eventfeed = await EventFeedManager.acreate_event(
                    self.contest,
                    str(idx),
                    EventFeedKind.CONTEST,
                    { "content": f"{visname}+{username}" },
                    viskind,
                    user
                )

                self.assertEqual(
                    json.loads( eventfeed.full_payload.decode() ),
                    {
                        "token": str(eventfeed.pk),
                        "id": str(idx),
                        "type": "contests",
                        "data": { "content": f"{visname}+{username}" }
                    }
                )

                self.apayloads[f"{visname}+{username}"] = (
                    eventfeed,
                    eventfeed.full_payload
                )
    @override_layer()
    def test_sudo_read_from_layer (self):
        self.consumer = FakeEventFeedConsumer(
            get_channel_layer(),
            self.sudo,
            self.contest.pk
        )

        with self.assertRaises(asyncio.TimeoutError):
            async def local_run ():
                await asyncio.wait_for( asyncio.gather(
                    self.createObjectsAsync(),
                    self.consumer.handle(b"") ),
                    timeout = 0.5 )
            asyncio.run( local_run() )
        
        self.verify_consumer(
            self.apayloads["public+null"],
            self.apayloads["public+user"],
            self.apayloads["public+sudo"],
            self.apayloads["private+null"],
            self.apayloads["private+user"],
            self.apayloads["private+sudo"], status = 200)
    @override_layer()
    def test_user_read_from_layer (self):
        self.consumer = FakeEventFeedConsumer(
            get_channel_layer(),
            self.user,
            self.contest.pk
        )

        with self.assertRaises(asyncio.TimeoutError):
            async def local_run ():
                await asyncio.wait_for( asyncio.gather(
                    self.createObjectsAsync(),
                    self.consumer.handle(b"") ),
                    timeout = 0.5 )
            asyncio.run( local_run() )
        
        self.verify_consumer(
            self.apayloads["public+null"],
            self.apayloads["public+user"],
            self.apayloads["public+sudo"],
            self.apayloads["private+user"], status = 200)
    @override_layer()
    def test_anonymous_read_from_layer (self):
        self.consumer = FakeEventFeedConsumer(
            get_channel_layer(),
            AnonymousUser(),
            self.contest.pk
        )

        with self.assertRaises(asyncio.TimeoutError):
            async def local_run ():
                await asyncio.wait_for( asyncio.gather(
                    self.createObjectsAsync(),
                    self.consumer.handle(b"") ),
                    timeout = 0.5 )
            asyncio.run( local_run() )
        
        self.verify_consumer(
            self.apayloads["public+null"],
            self.apayloads["public+user"],
            self.apayloads["public+sudo"], status = 200)

    @override_layer()
    def test_sudo_read_since (self):
        self.createObjects()
        
        self.consumer = FakeEventFeedConsumer(
            get_channel_layer(),
            self.sudo,
            self.contest.pk,
            since = self.payloads["private+null"][0].pk
        )

        with self.assertRaises(asyncio.TimeoutError):
            async def local_run ():
                await asyncio.wait_for( asyncio.gather(
                    self.createObjectsAsync(),
                    self.consumer.handle(b"") ),
                    timeout = 0.5 )
            asyncio.run( local_run() )
            
        self.verify_consumer(
            self.payloads["private+user"],
            self.payloads["private+sudo"],
            self.apayloads["public+null"],
            self.apayloads["public+user"],
            self.apayloads["public+sudo"],
            self.apayloads["private+null"],
            self.apayloads["private+user"],
            self.apayloads["private+sudo"], status = 200)
    @override_layer()
    def test_sudo_read_slow_db_no_doubles (self):
        """
        In this test, the query for the latest id
        is slowed down by a lot so both the message
        is received by the layer and the object is
        seen in database, so we are sure that the
        consumer does not send twice the same event.
        """
        self.createObjects()
        
        self.consumer = FakeEventFeedConsumer(
            get_channel_layer(),
            self.sudo,
            self.contest.pk
        )

        afind_latest = EventFeedManager.afind_latest
        async def custom_afind_latest ():
            await asyncio.sleep(0.5)
            result = await afind_latest()
            return result

        with patch ("ccs.models.managers.eventfeed.EventFeedManager.afind_latest", side_effect=custom_afind_latest):
            with self.assertRaises(asyncio.TimeoutError):
                async def local_run ():
                    await asyncio.wait_for( asyncio.gather(
                        self.createObjectsAsync(),
                        self.consumer.handle(b"") ),
                        timeout = 1 )
                asyncio.run( local_run() )
                
            self.verify_consumer(
                self.payloads["public+null"],
                self.payloads["public+user"],
                self.payloads["public+sudo"],
                self.payloads["private+null"],
                self.payloads["private+user"],
                self.payloads["private+sudo"],
                self.apayloads["public+null"],
                self.apayloads["public+user"],
                self.apayloads["public+sudo"],
                self.apayloads["private+null"],
                self.apayloads["private+user"],
                self.apayloads["private+sudo"], status = 200)

    @override_layer()
    @override_settings(EVENTFEED_HEARTBEET_TIME = 1)
    def test_sudo_read_heartbeat (self):
        self.consumer = FakeEventFeedConsumer(
            InMemoryChannelLayer(),
            self.sudo,
            self.contest.pk
        )
        
        with self.assertRaises(asyncio.TimeoutError):
            async def local_run ():
                await asyncio.wait_for( 
                    self.consumer.handle(b""),
                    timeout = 1.33 )
            asyncio.run( local_run() )
        
        _body = b"".join(self.consumer._bodies)
        assert _body == b"\n"
    @override_layer()
    @override_settings(EVENTFEED_HEARTBEET_TIME = 1)
    def test_user_read_heartbeat_private_does_not_reset (self):
        self.consumer = FakeEventFeedConsumer(
            InMemoryChannelLayer(),
            self.user,
            self.contest.pk
        )
        
        with self.assertRaises(asyncio.TimeoutError):
            async def try_private_reset ():
                await asyncio.sleep(0.5)
                await EventFeedManager.acreate_event( self.contest, "3", EventFeedKind.CONTEST, {}, Visibility.PRIVATE, None )
            async def local_run ():
                await asyncio.wait_for( 
                    asyncio.gather(
                        self.consumer.handle(b""),
                        try_private_reset()
                    ),
                    timeout = 1.33 )
            asyncio.run( local_run() )
        
        _body = b"".join(self.consumer._bodies)
        assert _body == b"\n"
    @override_layer(EVENTFEED_HEARTBEET_TIME = 1)
    def test_user_read_heartbeat_public_does_reset (self):
        self.consumer = FakeEventFeedConsumer(
            get_channel_layer(),
            self.user,
            self.contest.pk
        )
        
        with self.assertRaises(asyncio.TimeoutError):
            async def try_private_reset ():
                await asyncio.sleep(0.5)
                await EventFeedManager.acreate_event( self.contest, "3", EventFeedKind.CONTEST, {}, Visibility.PUBLIC, None )
            async def local_run ():
                await asyncio.wait_for( 
                    asyncio.gather(
                        self.consumer.handle(b""),
                        try_private_reset()
                    ),
                    timeout = 1.33 )
            asyncio.run( local_run() )
        
        _body = b"".join(self.consumer._bodies)
        self.assertEqual( _body, EventFeed.objects.all()[0].full_payload )
