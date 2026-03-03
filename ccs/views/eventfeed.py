
import asyncio
import datetime
import json
import logging
from urllib.parse import parse_qs

from channels.generic.http import AsyncHttpConsumer
from django.conf import settings
from django.contrib.auth.models import User
from rules.predicates import is_staff

from ccs.models.contest import Contest
from ccs.models.eventfeed import EventFeed

from asgiref.sync import sync_to_async

from ccs.models.managers.eventfeed import EventFeedManager, EventFeedMessage

class EventFeedConsumer (AsyncHttpConsumer):
    user: User

    async def contest_does_not_exist (self):
        await self.send_response(
            404, b'{ "code": 404, "message": "Contest does not exist." }',
            headers = [ (b"Content-Type", b"application/json") ]
        )

    async def handle (self, body):
        self.user = self.scope["user"]

        contest_id = int( self.scope["url_route"]["kwargs"].get('id') )

        raw_query_string = self.scope['query_string'].decode('utf-8')
        get_params = parse_qs(raw_query_string)
        
        since_token = get_params.get("since_token", [None])[0]
        if since_token is not None:
            since_token = int(since_token)

        try:
            contest = await Contest.objects.aget(pk = contest_id)
        except Contest.DoesNotExist:
            return await self.contest_does_not_exist()
        
        if not await sync_to_async(self.user.has_perm)("contest.view", contest):
            return await self.contest_does_not_exist()
        
        self.subscription_channel = await self.channel_layer.new_channel()
        await self.channel_layer.group_add(contest.eventfeed_group, self.subscription_channel)

        try:
            self.upto_id = upto_id = await EventFeedManager.afind_latest()

            await self.send_headers(status = 200, headers = [ (b"Content-Type", b"application/x-ndjson") ])
            
            async for event in EventFeedManager.get_feed_queryset(contest, self.user, upto_id, since=since_token):
                await self.send_body(event.full_payload, more_body=True)

            while True:
                try:
                    message = await asyncio.wait_for(
                        self.find_event_feed_message(),
                        timeout = settings.EVENTFEED_HEARTBEET_TIME
                    )

                    await self.send_body(message["payload"], more_body=True)
                except asyncio.TimeoutError:
                    # heartbeat
                    await self.send_body(b"\n", more_body=True)
        finally:
            await self.channel_layer.group_discard(contest.eventfeed_group, self.subscription_channel)

    def is_event_feed_message_valid (self, event: EventFeedMessage):
        return ( \
               event["owner_pk"]   == self.user.pk != None \
            or event["visibility"] == "public" \
            or is_staff(self.user) \
        ) and event["event_id"] > self.upto_id
    
    async def find_event_feed_message (self) -> EventFeedMessage:
        while True:
            message = await self.channel_layer.receive(self.subscription_channel)
            
            if self.is_event_feed_message_valid(message):
                return message
